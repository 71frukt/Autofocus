# Автофокус

## Сборка и запуск

### Тестовое окружение на python
```zsh
git clone https://github.com/71frukt/Autofocus.git
cd Autofocus
```

* В папку `lib` необходимо добавить модуль `window_final`


Создание виртуального окружения python
```zsh
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Запуск 
```zsh
./.venv/bin/python main.py
```

### Модуль на FPGA

```zsh
mkdir -p fpga/build && cd fpga/build
vivado
```

в tcl консоли:
```
source ../create_project.tcl
```