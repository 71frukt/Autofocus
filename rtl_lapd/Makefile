# симулятор по умолчанию
SIM ?= icarus

# язык, на котором написан RTL (SystemVerilog)
TOPLEVEL_LANG ?= verilog

# Список всех исходных файлов железа
VERILOG_SOURCES += $(shell pwd)/lapd_core.sv

# модуль верхнего уровня
TOPLEVEL = lapd_core

# Python-файл, в котором лежат тесты
MODULE = lapd_tb

# стандартные правила сборки Cocotb
include $(shell cocotb-config --makefiles)/Makefile.sim