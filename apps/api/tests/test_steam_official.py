"""模拟响应仅用于验证传输与访问限制；不声明任何 Steam 行情字段契约。"""
import json

import httpx
import pytest
from app.catalog import stable_id
from app.models import Price, SourceGrant
from app.steam_official import ENDPOINT, SteamConfig, SteamUnavailable, probe, readiness
from sqlalchemy import select

from tests.test_catalog import approve

KEY = 'TEST_ONLY_SECRET_NOT_A_REAL_KEY'


def enabled(db):
    approve(db, 'steam_official')
    db.add(SourceGrant(id=stable_id('test-steam-grant'), source_id=stable_id('source:steam_official'),
                       dataset='prices', license_reference='TEST ONLY simulated rights', enabled=True))
    db.commit()
    return SteamConfig(KEY, True, True)


def test_default_disabled_never_requests_network(db):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200)
    assert readiness(db, SteamConfig())['can_probe'] is False
    with pytest.raises(SteamUnavailable, match='未启用'):
        probe(db, SteamConfig(), httpx.MockTransport(handler))
    assert calls == []


def test_key_never_in_repr_url_or_archive_and_raw_not_prices(db, caplog):
    config = enabled(db)
    payload = '{"TEST_ONLY_UNVERIFIED_FIELD":1234567890123456789.01}'
    def handler(request):
        assert str(request.url).startswith(ENDPOINT)
        assert dict(request.url.params) == {'appid': '730'}
        assert request.headers['x-webapi-key'] == KEY
        assert 'cookie' not in request.headers
        assert 'key=' not in str(request.url)
        return httpx.Response(200, headers={'Content-Type': 'application/json'}, content=payload)
    result = probe(db, config, httpx.MockTransport(handler))
    assert result['payload_json'] == payload
    assert result['status'] == 'unavailable'
    assert result['transport_status'] == 'received_unverified'
    assert db.scalars(select(Price)).all() == []
    assert KEY not in repr(config) + json.dumps(result) + caplog.text


@pytest.mark.parametrize('status,content_type,payload,code', [
    (401, 'application/json', '{}', 'access_denied'),
    (403, 'application/json', '{}', 'access_denied'),
    (429, 'application/json', '{}', 'rate_limited'),
    (302, 'text/html', '', 'redirect_blocked'),
    (503, 'text/html', 'error', 'upstream_error'),
    (200, 'text/html', '<html>login</html>', 'unexpected_content'),
    (200, 'application/json', '{bad', 'invalid_json'),
    (200, 'application/json', '{"test":NaN}', 'invalid_json'),
    (200, 'application/json', 'true', 'invalid_json'),
    (200, 'application/json', '{"success":false}', 'upstream_rejected'),
    (200, 'application/json', '{"result":{"success":false}}', 'upstream_rejected'),
    (200, 'application/json', '{"key":"' + KEY + '"}', 'credential_echo'),
])
def test_upstream_rejections_do_not_retry_or_guess_prices(db, status, content_type, payload, code):
    config = enabled(db)
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={'Content-Type': content_type, 'Retry-After': '120',
                                              'Location': 'https://example.invalid/login'}, content=payload)
    with pytest.raises(SteamUnavailable) as failure:
        probe(db, config, httpx.MockTransport(handler))
    assert failure.value.code == code
    assert len(calls) == 1
    assert KEY not in str(failure.value)
    if status == 429:
        assert failure.value.retry_after == 120
    assert db.scalars(select(Price)).all() == []


def test_timeout_is_sanitized(db):
    config = enabled(db)
    def handler(request):
        raise httpx.ConnectTimeout(KEY, request=request)
    with pytest.raises(SteamUnavailable) as failure:
        probe(db, config, httpx.MockTransport(handler))
    assert failure.value.code == 'network_error'
    assert KEY not in str(failure.value)


def test_oversized_response_is_not_saved(db, monkeypatch):
    config = enabled(db)
    monkeypatch.setattr('app.steam_official.MAX_BYTES', 8)
    with pytest.raises(SteamUnavailable) as failure:
        probe(db, config, httpx.MockTransport(lambda _: httpx.Response(200, content='{"too_big":123}',
                                                    headers={'Content-Type': 'application/json'})))
    assert failure.value.code == 'response_too_large'


def test_revoked_grant_or_missing_app_permission_blocks_request(db):
    config = enabled(db)
    assert readiness(db, config)['can_probe'] is True
    assert readiness(db, SteamConfig(KEY, True, False))['can_probe'] is False
    grant = db.scalar(select(SourceGrant))
    grant.enabled = False
    db.commit()
    assert readiness(db, config)['can_probe'] is False


def test_cli_private_archive_and_no_payload_on_stdout(db, monkeypatch, tmp_path, capsys):
    import os
    import sys
    from contextlib import nullcontext

    from app import steam_official

    config = enabled(db)
    target = tmp_path / 'sample.steam-evidence.json'
    payload = '{"TEST_ONLY_UNVERIFIED_FIELD":123}'
    real_probe = steam_official.probe
    monkeypatch.setattr(steam_official.SteamConfig, 'from_env', lambda: config)
    monkeypatch.setattr(steam_official, 'SessionLocal', lambda: nullcontext(db))
    monkeypatch.setattr(steam_official, 'probe', lambda session, settings: real_probe(
        session, settings, httpx.MockTransport(lambda _: httpx.Response(
            200, content=payload, headers={'Content-Type': 'application/json'}))))
    monkeypatch.setattr(sys, 'argv', ['steam_official', 'probe', '--out', str(target)])
    assert steam_official.main() == 0
    assert os.stat(target).st_mode & 0o777 == 0o600
    assert json.loads(target.read_text())['payload_json'] == payload
    output = capsys.readouterr().out
    assert 'TEST_ONLY_UNVERIFIED_FIELD' not in output
    assert KEY not in output + target.read_text()
    with pytest.raises(SystemExit):
        steam_official.main()
    assert json.loads(target.read_text())['payload_json'] == payload
