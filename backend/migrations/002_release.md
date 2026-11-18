# 002 组合发布与保密联立检查

新增两张业务表，SQLAlchemy 启动自动创建；已有数据库升级需先备份。

## release_profiles（按报告冻结版本的保密配置）
- `checksum` 唯一，对应报告冻结快照 SHA256；同版报告共享一份配置。
- `departments` 该版本部门全集（由已完成报告透视结果汇总，有序）；`confidential` 保密部门子集；`note` 配置说明。
- 由 admin 通过 `POST /release-profiles` 按 `run_id` 登记或覆盖更新。

## release_publications（组合发布登记与裁决记录）
- `request_key` 唯一幂等键：崩溃恢复后同键重试返回原记录，不重复发布；同键不同参数返回 409。
- `checksum` 冻结版本；`coefficients` 部门→有理数系数（字符串，如 `1/2`）；`value` 精确组合金额（有理数串，分）。
- `status`：published / rejected / withdrawn。rejected 记录保留拒绝推导 `derivation`；withdrawn 不可下载但方程仍参与后续联立检查。
- `payload` 可下载内容与登记在同一事务原子生效；`reason` 记录允许或拒绝原因。

## 裁决与一致性
- 发布时对 `release_profiles` 行 `SELECT ... FOR UPDATE`，同版并发发布串行联合裁决；单事务写入登记、内容与审计。
- 准入消元在 `services/release_math.py`，独立复算在 `services/release_verify.py`（`GET /releases/verify/{checksum}`）。
- 阅读者原有整表下载入口（`/runs/{id}/csv`、`/deliveries/{id}/csv`）在版本配置保密部门后返回 403。
