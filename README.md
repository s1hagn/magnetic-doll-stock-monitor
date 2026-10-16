# RIIZE MAGNETIC DOLL 补货监控

监控 [SMTOWN &STORE RIIZE MAGNETIC DOLL](https://smtownandstore.com/product/riize-concert-tour-riizing-loud-finale-in-seoul-magnetic-doll/28247/category/2003/display/1/) 的六个独立选项：SHOTARO、EUNSEOK、SUNGCHAN、WONBIN、SOHEE、ANTON。

使用 Playwright Chromium 执行商城网页 JavaScript，再读取六位成员的库存选项；每 5 分钟尝试检查一次。发现任意成员从 SOLD OUT 变为可购买时，向 **siya2026z@gmail.com** 发送邮件。持续有货只发一次；再次售罄后补货会再次提醒。首次启动发送启用通知（如首次即有货，则直接发送补货通知）。

## 配置（必须先完成）
在本仓库 **Settings → Secrets and variables → Actions → Repository secrets** 中创建：

- `GMAIL_USER`：和之前 NMIXX 监控一样的 Gmail 发件邮箱。
- `GMAIL_APP_PASSWORD`：同一 Gmail 的应用专用密码（不要提交到仓库，也不要在聊天里提供）。

这是新仓库，GitHub Secrets **不会从 NMIXX 仓库自动复制**。收件邮箱已经在 workflow 中固定为 `siya2026z@gmail.com`。

GitHub Actions 已配置 `*/5 * * * *`，自动定时运行 **一次正式检查**（`check`），无需手动启动 `bootstrap`。手动运行可以选择 `inspect`（仅查看库存）、`test-email`（测试 SMTP）或 `check`（正式检查一次）。旧版 `bootstrap` / `watch` 已移除；旧版长时间运行任务需要等待结束或手动取消。

## 注意
- 渲染后的选项文字中出现 SOLD OUT 时标为售罄；若六位全部没有明确的售罄标记，则暂时保守报错而不是假报全员补货。缺少任何一个选项、网页异常或页面格式变化时也会失败并保留原有状态。此方法仍需要通过 inspect 实际验证。
- GitHub Actions 的定时触发可能延迟、跳过或停用；5 分钟是目标检查间隔，不是严格时间保证。
- 通过 `stock-state.json` 保存上次状态；如邮件已发送但状态 Git 提交失败，可能出现重复提醒。
- 在 Actions 中查看运行记录。没有补货邮件不代表任务一定正常。
- 停止监控时禁用 workflow，并取消正在运行的任务。
- 每次任务只检查一次，不再采用持续约 1 小时的长任务或自动续跑链。GitHub cron 的执行可能延迟、跳过或在仓库长时间无活动后停用；请定期查看 Actions。\n- `concurrency` 防止多轮库存检查同时写入状态；极少数拥堵情况下旧的排队任务仍可能被新任务替换。
