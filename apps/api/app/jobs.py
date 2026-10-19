from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.catalog import ImportConflict
from app.models import ImportJob, now


def run_import(db: Session, provider: str, kind: str, action: Callable[[], dict]) -> dict:
    job_id = str(uuid4())
    started = now()
    try:
        job = ImportJob(id=job_id, provider=provider, job_type=kind, status='running', requested_at=started, started_at=started)
        db.add(job)
        result = action()
        job.status = 'completed'
        job.completed_at = now()
        db.commit()
        return {**result, 'job_id': job_id}
    except (PermissionError, ImportConflict, IntegrityError) as exc:
        db.rollback()
        status = 403 if isinstance(exc, PermissionError) else 409
        reason = '数据集未获授权' if status == 403 else '映射未知或原始记录冲突，整批已回滚'
        # 失败审计不记录导入正文、密钥或数据库错误细节。
        db.add(ImportJob(id=job_id, provider=provider, job_type=kind, status='failed',
                         requested_at=started, started_at=started, completed_at=now(), error_summary=reason))
        db.commit()
        raise HTTPException(status, reason) from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, '导入存储暂时不可用，请稍后重试') from None
