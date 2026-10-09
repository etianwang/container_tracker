# 宝塔部署

这是 PHP 页面调用短生命周期 Python 查询进程的应用，Python 不需要常驻服务。

## 1. 上传

将 `container-tracker-baota.zip` 上传到宝塔站点根目录并解压。站点运行目录就是包含 `index.php` 的目录。

## 2. PHP

在宝塔为该站点选择 PHP 8.1 或更高版本，并启用 `pdo_sqlite`、`sqlite3`、`mbstring` 扩展。不要在 PHP 的 `disable_functions` 中禁用 `exec`、`shell_exec` 或 `proc_open`。

将站点目录及其下的 `data/` 目录设置为网站运行用户可写。首次访问会自动创建 SQLite 数据库和日志目录。

## 3. Python 与浏览器

安装 Python 3.12、Google Chrome 或 Chromium。进入站点目录后执行：

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

在宝塔的 PHP-FPM 配置中添加环境变量，使 PHP 使用该虚拟环境：

```ini
env[TRACKER_PYTHON] = /www/wwwroot/你的站点目录/.venv/bin/python
```

保存后重载 PHP-FPM。若未设置此变量，程序默认执行 `python3.12`。

如需启用 17TRACK 综合查询，在宝塔终端执行以下命令，将自己的密钥保存到站点运行用户可读、其他用户不可读的位置：

```bash
mkdir -p data
printf '%s' '你的17TRACK密钥' > data/17track.key
chmod 600 data/17track.key
```

也可以在 PHP-FPM 与 Python 环境中设置同名环境变量 `TRACK17_TOKEN`。密钥文件已被 Git 忽略，不能提交或打进上传包。

## 4. 验证

打开站点首页，输入自己的有效箱号。首次查询会启动一次 Python/Chrome 子进程，结束后会自动退出；查询失败详情位于 `data/logs/tracker.log`。

## 注意

- Maersk、MSC、COSCO 为站内自动查询，服务器需要能访问承运商官网。
- 配置 17TRACK 后，除 Maersk、MSC、COSCO 外的自动识别前缀会优先由它查询；其注册查询按 17TRACK 账户规则消耗额度。
- OOCL、Hapag-Lloyd、ONE、ZIM 打开官网让用户完成交互或验证码。
- 不要把 `data/` 目录上传到 Git；其中包含本地历史记录、缓存和日志。
