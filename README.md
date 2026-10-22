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


## 新增：BABY RIIZE KEY RING（六人选项）

同一个 workflow 现在也监控 [RIIZE 2025 WE LITTLE RIIZE – BABY RIIZE KEY RING](https://smtownandstore.com/product/pop-up-riize-2025-we-little-riize-baby-riize-key-ring/26236/category/57/display/1/) 的 SHOTARO、EUNSEOK、SUNGCHAN、WONBIN、SOHEE、ANTON 六人款。

- `monitor.py` 和 `stock-state.json`：原有 MAGNETIC DOLL，保持独立。
- `baby_riize_monitor.py` 和 `baby-riize-state.json`：新增钥匙扣，保持独立。
- 同一轮依次执行两个监控；任意一款监控失败都不会跳过另一款。
- 两款均使用已有 Gmail Secrets 和相同收件地址；邮件主题会注明商品名称。
- 新商品首次成功运行发送启用邮件；其后只有首次发现可购买、或从售罄变有货才通知。
- 若商品页面无法识别全部六个选项，或全部六个都没有明确售罄标识，会保守报错而不发送假补货提醒。这也意味着真正六款同时有货时需要人工检查日志。
- 在 **Actions → RIIZE magnetic doll + baby key ring restock alert → Run workflow → inspect** 先检查两个商品的选项解析。inspect 不发邮件或写状态。之后用 `check` 正式初始化两款库存状态。
- GitHub Actions 目标每小时启动一轮，每轮至多 12 次，轮次间隔目标 5 分钟；并非保证每 5 分钟必定执行。

