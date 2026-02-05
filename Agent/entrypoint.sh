#!/bin/bash

# 配置 FreeTDS ODBC 驅動

# 創建 ODBC 配置目錄
mkdir -p /root/.odbc.ini

# 寫入 ODBC 驅動配置
cat > /etc/odbcinst.ini << 'EOF'
[FreeTDS]
Description = FreeTDS driver
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so
UsageCount = 1

[ODBC]
Trace = No
TraceFile = /tmp/odbc.log
EOF

# 啟動應用
exec python main.py
