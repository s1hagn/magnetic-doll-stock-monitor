# RIIZE MAGNETIC DOLL 补货监控

监控 [SMTOWN &STORE RIIZE MAGNETIC DOLL](https://smtownandstore.com/product/riize-concert-tour-riizing-loud-finale-in-seoul-magnetic-doll/28247/category/2003/display/1/) 的六个独立选项：SHOTARO、EUNSEOK、SUNGCHAN、WONBIN、SOHEE、ANTON。

使用 Playwright Chromium 执行商城网页 JavaScript，再读取六位成员的库存选项；每 5 分钟尝试检查一次。发现任意成员从 SOLD OUT 变为可购买时，向 **siya2026z@gmail.com** 发送邮件。持续有货只发一次；再次售罄后补货会再次提醒。首次启动发送启用通知（如首次即有货，则直接发送补货通知）。

## 配置（必须先完成）
在本仓库 **Settings → Secrets and variables → Actions → Repository secrets** 中创建：

- `GMAIL_USER`：和之前 NMIXX 监控一样的 Gmail 发件邮箱。
- `GMAIL_APP_PASSWORD`：同一 Gmail 的应用专用密码（不要提交到仓库，也不要在聊天里提供）。

这是新仓库，GitHub Secrets **不会从 NMIXX 仓库自动复制**。收件邮箱已经在 workflow 中固定为 `siya2026z@gmail.com`。

GitHub Actions 使用 `0 * * * *`：**目标每小时启动一轮，轮内检查 12 次，每次间隔约 5 分钟**，共约 56 分钟。无需手动启动；也不使用自动续跑链。定时触发不保证准点，可能延迟或跳过。手动运行可选 `inspect`（只看库存）、`test-email`（测试 SMTP）、`check`（单次正式检查）、`watch`（完整 12 次连续检查）。通常不需要手动点 `watch`，以免与每小时的自动任务冲突。

## 注意
- 渲染后的选项文字中出现 SOLD OUT 时标为售罄；若六位全部没有明确的售罄标记，则暂时保守报错而不是假报全员补货。缺少任何一个选项、网页异常或页面格式变化时也会失败并保留原有状态。此方法仍需要通过 inspect 实际验证。
- GitHub Actions 的定时触发可能延迟、跳过或停用；5 分钟是目标检查间隔，不是严格时间保证。
- 通过 `stock-state.json` 保存上次状态；如邮件已发送但状态 Git 提交失败，可能出现重复提醒。
- 在 Actions 中查看运行记录。没有补货邮件不代表任务一定正常。
- 停止监控时禁用 workflow，并取消正在运行的任务。
- 每小时一轮长任务，内部检查 12 次，避免每 5 分钟创建一条工作流记录；每轮上限为 65 分钟。没有自动续跑链。GitHub cron 可能延迟、跳过或在仓库长时间无活动后停用，请定期检查。\n- `concurrency` 防止多轮库存检查同时写入状态；若上一轮延迟而与下一轮重叠，仍可能排队，且 GitHub 只保留一个待运行的并发任务。
