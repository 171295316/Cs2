export const definitions: Record<string, string> = {
  observed_distinct_instances: '已发现独立实例数', public_inventory_units: '公开库存可见样本',
  listed_units: '平台在售数量', estimated_total_units: '有依据的估算总量',
};
export function exactAmount(value: string, exponent: number) {
  const padded = value.padStart(exponent + 1, '0');
  return exponent ? `${padded.slice(0, -exponent)}.${padded.slice(-exponent)}` : padded;
}
