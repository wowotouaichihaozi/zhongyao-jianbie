"""MCU lab catalog, routing, recommendation, and virtual-flash validation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit


CATALOG_VERSION = "2.0.0"

OPEN_SOURCE_REFERENCES = [
    {
        "id": "arduino-examples",
        "name": "Arduino IDE bundled examples",
        "url": "https://github.com/arduino/arduino-examples",
        "license": "CC0-1.0",
        "usage": "实验主题、基础代码结构与接线原理参考",
    },
    {
        "id": "wokwi-elements",
        "name": "Wokwi Elements",
        "url": "https://github.com/wokwi/wokwi-elements",
        "license": "MIT",
        "usage": "浏览器电子元件视觉组件",
    },
    {
        "id": "avr8js",
        "name": "AVR8js",
        "url": "https://github.com/wokwi/avr8js",
        "license": "MIT",
        "usage": "ATmega328P 指令级仿真架构参考",
    },
    {
        "id": "learn-8051",
        "name": "Learn 8051",
        "url": "https://github.com/kopytjuk/learn-8051",
        "license": "MIT",
        "usage": "8051 汇编、堆栈、七段数码管实验参考",
    },
    {
        "id": "emu8051",
        "name": "emu8051",
        "url": "https://github.com/jarikomppa/emu8051",
        "license": "MIT",
        "usage": "MCS-51 指令与特殊功能寄存器行为核验",
    },
]


def _pin(
    pin_id: str,
    label: str,
    physical: str,
    side: str,
    order: int,
    capabilities: list[str],
    note: str = "",
) -> dict[str, Any]:
    return {
        "id": pin_id,
        "label": label,
        "physicalPin": physical,
        "side": side,
        "order": order,
        "capabilities": capabilities,
        "note": note,
    }


def _arduino_pins() -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    pwm = {3, 5, 6, 9, 10, 11}
    interrupts = {2, 3}
    for order, number in enumerate(range(13, -1, -1)):
        capabilities = ["digital-input", "digital-output", "digital-io"]
        notes = []
        if number in pwm:
            capabilities.append("pwm")
            notes.append("PWM")
        if number in interrupts:
            capabilities.append("external-interrupt")
            notes.append(f"INT{0 if number == 2 else 1}")
        if number == 0:
            capabilities.append("uart-rx")
            notes.append("RX")
        elif number == 1:
            capabilities.append("uart-tx")
            notes.append("TX")
        if number == 10:
            capabilities.append("spi-ss")
        elif number == 11:
            capabilities.append("spi-mosi")
        elif number == 12:
            capabilities.append("spi-miso")
        elif number == 13:
            capabilities.append("spi-sck")
        pins.append(_pin(f"D{number}", f"D{number}", str(number), "left", order, capabilities, " / ".join(notes)))

    for order, number in enumerate(range(6)):
        capabilities = ["analog-input", "digital-input", "digital-output", "digital-io"]
        note = "ADC"
        if number == 4:
            capabilities.append("i2c-sda")
            note = "ADC / SDA"
        elif number == 5:
            capabilities.append("i2c-scl")
            note = "ADC / SCL"
        pins.append(_pin(f"A{number}", f"A{number}", f"A{number}", "right", order, capabilities, note))

    power_pins = [
        ("AREF", "AREF", "reference", "ADC 参考电压"),
        ("RESET", "RESET", "reset", "低电平复位"),
        ("3V3", "3.3V", "power-3v3", "3.3V 电源"),
        ("5V", "5V", "power-5v", "5V 电源"),
        ("GND1", "GND", "ground", "公共地"),
        ("GND2", "GND", "ground", "公共地"),
        ("VIN", "VIN", "power-in", "外部输入电源"),
        ("IOREF", "IOREF", "reference", "I/O 电平参考"),
    ]
    offset = 6
    for index, (pin_id, label, capability, note) in enumerate(power_pins):
        pins.append(_pin(pin_id, label, pin_id, "right", offset + index, [capability], note))
    return pins


def _mcs51_pins() -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    for bit in range(8):
        pins.append(_pin(f"P1.{bit}", f"P1.{bit}", str(bit + 1), "left", bit, ["digital-input", "digital-output", "digital-io"], "准双向 I/O"))
    pins.append(_pin("RST", "RST", "9", "left", 8, ["reset"], "高电平保持两个机器周期复位"))
    alternate = {
        0: ("RXD", "uart-rx"),
        1: ("TXD", "uart-tx"),
        2: ("INT0", "external-interrupt"),
        3: ("INT1", "external-interrupt"),
        4: ("T0", "timer-input"),
        5: ("T1", "timer-input"),
        6: ("WR", "external-memory-control"),
        7: ("RD", "external-memory-control"),
    }
    for bit in range(8):
        alt_name, alt_capability = alternate[bit]
        pins.append(
            _pin(
                f"P3.{bit}",
                f"P3.{bit}",
                str(10 + bit),
                "left",
                9 + bit,
                ["digital-input", "digital-output", "digital-io", alt_capability],
                f"准双向 I/O / {alt_name}",
            )
        )
    pins.extend(
        [
            _pin("XTAL2", "XTAL2", "18", "left", 17, ["clock-output"], "晶振输出"),
            _pin("XTAL1", "XTAL1", "19", "left", 18, ["clock-input"], "晶振输入"),
            _pin("GND", "GND", "20", "left", 19, ["ground"], "公共地"),
        ]
    )

    right_physical = [
        ("VCC", "VCC", "40", ["power-5v"], "5V 电源"),
        ("P0.0", "P0.0", "39", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.1", "P0.1", "38", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.2", "P0.2", "37", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.3", "P0.3", "36", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.4", "P0.4", "35", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.5", "P0.5", "34", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.6", "P0.6", "33", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("P0.7", "P0.7", "32", ["digital-input", "digital-output", "digital-io", "open-drain", "address-data-bus"], "开漏 I/O，作普通输出需外接上拉"),
        ("EA", "EA", "31", ["program-memory-select"], "高电平使用片内程序存储器"),
        ("ALE", "ALE", "30", ["address-latch"], "地址锁存允许"),
        ("PSEN", "PSEN", "29", ["program-store-enable"], "外部程序存储器读选通"),
    ]
    for bit in range(7, -1, -1):
        right_physical.append((f"P2.{bit}", f"P2.{bit}", str(21 + bit), ["digital-input", "digital-output", "digital-io", "address-bus"], "准双向 I/O / 高位地址总线"))
    for order, (pin_id, label, physical, capabilities, note) in enumerate(right_physical):
        pins.append(_pin(pin_id, label, physical, "right", order, capabilities, note))
    return pins


MCU_BOARDS = [
    {
        "id": "arduino",
        "title": "Arduino Uno",
        "subtitle": "ATmega328P · 16 MHz · 5V",
        "mcu": "ATmega328P",
        "language": "Arduino C/C++",
        "logicVoltage": 5.0,
        "clockHz": 16_000_000,
        "pins": _arduino_pins(),
        "simulationBoundary": "支持教学代码子集、GPIO、ADC、PWM、串口及常用传感器状态联动；精确时序和电气负载需实板复验。",
    },
    {
        "id": "8051",
        "title": "8051 / AT89S52",
        "subtitle": "MCS-51 · 40 Pin DIP · 5V",
        "mcu": "AT89S52",
        "language": "MCS-51 Assembly",
        "logicVoltage": 5.0,
        "clockHz": 11_059_200,
        "pins": _mcs51_pins(),
        "simulationBoundary": "支持核心寄存器、内部 RAM、端口和常用跳转/算术指令；机器周期级外设时序需实板或完整指令级仿真器复验。",
    },
]


MCU_COMPONENTS = [
    {
        "id": "led-module",
        "label": "LED（含 220Ω）",
        "category": "输出",
        "visual": "led",
        "description": "内置限流电阻的数字输出指示灯。",
        "terminals": [
            {"id": "A", "label": "信号", "required": True, "accepts": ["digital-output", "pwm"]},
            {"id": "K", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "rgb-led-module",
        "label": "RGB LED（含限流）",
        "category": "输出",
        "visual": "rgb-led",
        "description": "共阴 RGB LED 模块，三个颜色通道可独立 PWM。",
        "terminals": [
            {"id": "R", "label": "R", "required": True, "accepts": ["digital-output", "pwm"]},
            {"id": "G", "label": "G", "required": True, "accepts": ["digital-output", "pwm"]},
            {"id": "B", "label": "B", "required": True, "accepts": ["digital-output", "pwm"]},
            {"id": "COM", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "led-bar",
        "label": "8 位 LED 灯条（含限流）",
        "category": "输出",
        "visual": "led-bar",
        "description": "每路内置 220Ω 限流电阻，适合端口和移位实验。",
        "terminals": [
            *[{"id": f"D{index}", "label": str(index), "required": True, "accepts": ["digital-output"]} for index in range(8)],
            {"id": "COM", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "pushbutton",
        "label": "轻触按键",
        "category": "输入",
        "visual": "button",
        "description": "下拉到 GND，建议配合内部上拉使用。",
        "terminals": [
            {"id": "SIG", "label": "信号", "required": True, "accepts": ["digital-input", "external-interrupt"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "potentiometer",
        "label": "10k 电位器",
        "category": "输入",
        "visual": "potentiometer",
        "description": "输出 0-5V 模拟电压。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "OUT", "label": "OUT", "required": True, "accepts": ["analog-input"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "photoresistor",
        "label": "光敏电阻模块",
        "category": "传感器",
        "visual": "photoresistor",
        "description": "输出随光照变化的模拟电压。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "AO", "label": "AO", "required": True, "accepts": ["analog-input"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "buzzer",
        "label": "有源蜂鸣器模块",
        "category": "输出",
        "visual": "buzzer",
        "description": "内置振荡与三极管驱动，使用数字电平控制。",
        "terminals": [
            {"id": "SIG", "label": "信号", "required": True, "accepts": ["digital-output", "pwm"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "servo",
        "label": "SG90 舵机",
        "category": "执行器",
        "visual": "servo",
        "description": "50Hz 控制脉冲；实板建议独立供电并与主板共地。",
        "terminals": [
            {"id": "SIG", "label": "PWM", "required": True, "accepts": ["pwm", "digital-output"]},
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "hc-sr04",
        "label": "HC-SR04 超声波",
        "category": "传感器",
        "visual": "hc-sr04",
        "description": "TRIG 触发，ECHO 脉宽对应距离。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "TRIG", "label": "TRIG", "required": True, "accepts": ["digital-output"]},
            {"id": "ECHO", "label": "ECHO", "required": True, "accepts": ["digital-input", "external-interrupt"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "dht22",
        "label": "DHT22 温湿度模块",
        "category": "传感器",
        "visual": "dht22",
        "description": "带 DATA 上拉电阻的单总线数字温湿度模块。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v", "power-3v3"]},
            {"id": "DATA", "label": "DATA", "required": True, "accepts": ["digital-input", "digital-output"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "seven-segment",
        "label": "一位数码管模块（含限流）",
        "category": "显示",
        "visual": "7segment",
        "description": "共阴极模块，A-DP 每段内置 330Ω 限流电阻。",
        "terminals": [
            *[{"id": segment, "label": segment, "required": True, "accepts": ["digital-output"]} for segment in ["A", "B", "C", "D", "E", "F", "G", "DP"]],
            {"id": "COM", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "lcd1602",
        "label": "LCD1602",
        "category": "显示",
        "visual": "lcd1602",
        "description": "四位数据总线模块；RW、对比度和背光网络在教学模型中已固定。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
            *[{"id": name, "label": name, "required": True, "accepts": ["digital-output"]} for name in ["RS", "E", "D4", "D5", "D6", "D7"]],
        ],
    },
    {
        "id": "oled-i2c",
        "label": "SSD1306 OLED",
        "category": "显示",
        "visual": "ssd1306",
        "description": "I2C OLED，Arduino Uno 使用 A4/SDA 与 A5/SCL。",
        "terminals": [
            {"id": "VCC", "label": "VCC", "required": True, "accepts": ["power-3v3", "power-5v"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
            {"id": "SDA", "label": "SDA", "required": True, "accepts": ["i2c-sda"]},
            {"id": "SCL", "label": "SCL", "required": True, "accepts": ["i2c-scl"]},
        ],
    },
    {
        "id": "relay",
        "label": "单路继电器模块",
        "category": "执行器",
        "visual": "relay",
        "description": "内置三极管和续流保护，逻辑输入控制线圈；仿真不接入市电负载。",
        "terminals": [
            {"id": "VCC", "label": "5V", "required": True, "accepts": ["power-5v"]},
            {"id": "IN", "label": "IN", "required": True, "accepts": ["digital-output"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "serial-monitor",
        "label": "串口终端",
        "category": "通信",
        "visual": "serial",
        "description": "交叉连接 MCU TX/RX，并保持共地。",
        "terminals": [
            {"id": "RX", "label": "RX", "required": True, "accepts": ["uart-tx"]},
            {"id": "TX", "label": "TX", "required": False, "accepts": ["uart-rx"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
    {
        "id": "crystal",
        "label": "11.0592MHz 晶振",
        "category": "基础",
        "visual": "crystal",
        "description": "8051 外部时钟网络的教学抽象。",
        "terminals": [
            {"id": "X1", "label": "XTAL1", "required": True, "accepts": ["clock-input"]},
            {"id": "X2", "label": "XTAL2", "required": True, "accepts": ["clock-output"]},
        ],
    },
    {
        "id": "reset-button",
        "label": "复位按键模块",
        "category": "基础",
        "visual": "button",
        "description": "带下拉和 RC 网络的高电平复位按键模块。",
        "terminals": [
            {"id": "RST", "label": "RST", "required": True, "accepts": ["reset"]},
            {"id": "VCC", "label": "VCC", "required": True, "accepts": ["power-5v"]},
            {"id": "GND", "label": "GND", "required": True, "accepts": ["ground"]},
        ],
    },
]


def _part(
    part_id: str,
    component_id: str,
    label: str,
    x: int,
    y: int,
    connections: dict[str, str],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": part_id,
        "componentId": component_id,
        "label": label,
        "x": x,
        "y": y,
        "connections": connections,
        "state": state or {},
    }


ARDUINO_EXPERIMENTS = [
    {
        "id": "uno-led-ready",
        "board": "arduino",
        "title": "01 · GPIO LED 闪烁",
        "summary": "验证输出模式、HIGH/LOW 电平与延时控制。",
        "difficulty": "入门",
        "durationMinutes": 15,
        "tags": ["GPIO", "数字输出", "LED", "延时"],
        "knowledgePoints": ["pinMode", "digitalWrite", "限流电阻"],
        "sourceIds": ["arduino-examples"],
        "code": """void setup() {
  pinMode(13, OUTPUT);
}

void loop() {
  digitalWrite(13, HIGH);
  delay(500);
  digitalWrite(13, LOW);
  delay(500);
}""",
        "parts": [_part("led-13", "led-module", "D13 LED", 290, 120, {"A": "D13", "K": "GND1"})],
        "acceptance": ["LED 以约 1Hz 周期闪烁", "D13 输出状态与执行日志一致", "LED 阴极连接 GND"],
    },
    {
        "id": "uno-button-ready",
        "board": "arduino",
        "title": "02 · 按键控制 LED",
        "summary": "使用 INPUT_PULLUP 消除悬空输入，建立输入到输出的闭环。",
        "difficulty": "入门",
        "durationMinutes": 20,
        "tags": ["GPIO", "按键", "输入上拉", "中断前置"],
        "knowledgePoints": ["INPUT_PULLUP", "digitalRead", "低电平有效"],
        "sourceIds": ["arduino-examples"],
        "code": """const int buttonPin = 2;
const int ledPin = 13;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  int state = digitalRead(buttonPin);
  digitalWrite(ledPin, state == LOW ? HIGH : LOW);
  delay(50);
}""",
        "parts": [
            _part("button-2", "pushbutton", "D2 按键", 250, 250, {"SIG": "D2", "GND": "GND1"}),
            _part("led-13", "led-module", "D13 LED", 300, 100, {"A": "D13", "K": "GND2"}),
        ],
        "acceptance": ["松开时 LED 熄灭", "按住时 LED 点亮", "D2 使用内部上拉且按键另一端接地"],
    },
    {
        "id": "uno-traffic-light",
        "board": "arduino",
        "title": "03 · 三色交通灯时序",
        "summary": "用三路 GPIO 建立互斥状态与顺序控制。",
        "difficulty": "入门",
        "durationMinutes": 25,
        "tags": ["GPIO", "交通灯", "状态机", "时序"],
        "knowledgePoints": ["多路输出", "状态切换", "互斥控制"],
        "sourceIds": ["arduino-examples"],
        "code": """void setup() {
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
}

void loop() {
  digitalWrite(8, HIGH); digitalWrite(9, LOW); digitalWrite(10, LOW); delay(1200);
  digitalWrite(8, LOW); digitalWrite(9, HIGH); digitalWrite(10, LOW); delay(400);
  digitalWrite(8, LOW); digitalWrite(9, LOW); digitalWrite(10, HIGH); delay(1000);
}""",
        "parts": [
            _part("red", "led-module", "红灯", 230, 95, {"A": "D8", "K": "GND1"}, {"color": "red"}),
            _part("yellow", "led-module", "黄灯", 230, 210, {"A": "D9", "K": "GND1"}, {"color": "yellow"}),
            _part("green", "led-module", "绿灯", 230, 325, {"A": "D10", "K": "GND1"}, {"color": "green"}),
        ],
        "acceptance": ["任意时刻仅一个灯点亮", "红黄绿按预设顺序切换", "三路 LED 共地"],
    },
    {
        "id": "uno-pwm-fade",
        "board": "arduino",
        "title": "04 · PWM 呼吸灯",
        "summary": "观察占空比变化对 LED 平均亮度的影响。",
        "difficulty": "基础",
        "durationMinutes": 25,
        "tags": ["PWM", "模拟输出", "呼吸灯", "定时器"],
        "knowledgePoints": ["analogWrite", "占空比", "PWM 引脚限制"],
        "sourceIds": ["arduino-examples"],
        "code": """void setup() {
  pinMode(9, OUTPUT);
}

void loop() {
  analogWrite(9, 32); delay(120);
  analogWrite(9, 96); delay(120);
  analogWrite(9, 180); delay(120);
  analogWrite(9, 255); delay(120);
  analogWrite(9, 96); delay(120);
}""",
        "parts": [_part("pwm-led", "led-module", "D9 PWM LED", 285, 150, {"A": "D9", "K": "GND1"})],
        "acceptance": ["LED 亮度随 PWM 值变化", "输出连接支持 PWM 的 D9", "PWM 值限制在 0-255"],
    },
    {
        "id": "uno-pot-serial",
        "board": "arduino",
        "title": "05 · 电位器 ADC 与串口",
        "summary": "采集 10 位 ADC，映射为 PWM 并通过串口输出。",
        "difficulty": "基础",
        "durationMinutes": 30,
        "tags": ["ADC", "电位器", "串口", "PWM", "数据映射"],
        "knowledgePoints": ["analogRead", "map", "Serial.println"],
        "sourceIds": ["arduino-examples"],
        "code": """void setup() {
  Serial.begin(9600);
  pinMode(9, OUTPUT);
}

void loop() {
  int sensor = analogRead(A0);
  int level = map(sensor, 0, 1023, 0, 255);
  analogWrite(9, level);
  Serial.println(sensor);
  delay(100);
}""",
        "parts": [
            _part("pot", "potentiometer", "A0 电位器", 220, 240, {"VCC": "5V", "OUT": "A0", "GND": "GND1"}, {"value": 512}),
            _part("pwm-led", "led-module", "D9 LED", 270, 95, {"A": "D9", "K": "GND2"}),
            _part("serial", "serial-monitor", "串口终端", 70, 390, {"RX": "D1", "TX": "D0", "GND": "GND1"}),
        ],
        "acceptance": ["电位器值覆盖 0-1023", "PWM 亮度跟随 ADC", "串口 RX 接主板 TX(D1)"],
    },
    {
        "id": "uno-light-alarm",
        "board": "arduino",
        "title": "06 · 光照阈值报警",
        "summary": "使用光敏模拟量触发蜂鸣器，练习阈值判断。",
        "difficulty": "基础",
        "durationMinutes": 30,
        "tags": ["ADC", "光敏", "蜂鸣器", "阈值"],
        "knowledgePoints": ["模拟采样", "比较运算", "tone"],
        "sourceIds": ["arduino-examples", "wokwi-elements"],
        "code": """void setup() {
  pinMode(8, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  int light = analogRead(A0);
  digitalWrite(8, light < 350 ? HIGH : LOW);
  Serial.println(light);
  delay(120);
}""",
        "parts": [
            _part("ldr", "photoresistor", "A0 光敏模块", 210, 230, {"VCC": "5V", "AO": "A0", "GND": "GND1"}, {"value": 650}),
            _part("buzzer", "buzzer", "D8 蜂鸣器", 285, 95, {"SIG": "D8", "GND": "GND2"}),
            _part("serial", "serial-monitor", "串口终端", 60, 390, {"RX": "D1", "TX": "D0", "GND": "GND1"}),
        ],
        "acceptance": ["光照值低于阈值时蜂鸣器有效", "串口持续输出采样值", "模拟输出只接 A0-A5"],
    },
    {
        "id": "uno-ultrasonic-distance",
        "board": "arduino",
        "title": "07 · 超声波测距",
        "summary": "产生 10us 触发脉冲，并将 ECHO 脉宽换算为距离。",
        "difficulty": "进阶",
        "durationMinutes": 40,
        "tags": ["超声波", "脉宽", "传感器", "串口"],
        "knowledgePoints": ["delayMicroseconds", "pulseIn", "时间换算"],
        "sourceIds": ["arduino-examples", "wokwi-elements"],
        "code": """void setup() {
  pinMode(7, OUTPUT);
  pinMode(6, INPUT);
  Serial.begin(9600);
}

void loop() {
  digitalWrite(7, LOW); delayMicroseconds(2);
  digitalWrite(7, HIGH); delayMicroseconds(10);
  digitalWrite(7, LOW);
  long duration = pulseIn(6, HIGH);
  long distance = duration / 58;
  Serial.println(distance);
  delay(200);
}""",
        "parts": [
            _part("sonar", "hc-sr04", "HC-SR04", 175, 160, {"VCC": "5V", "TRIG": "D7", "ECHO": "D6", "GND": "GND1"}, {"distanceCm": 35}),
            _part("serial", "serial-monitor", "串口终端", 70, 380, {"RX": "D1", "TX": "D0", "GND": "GND2"}),
        ],
        "acceptance": ["TRIG 脉冲宽度为约 10us", "ECHO 使用输入引脚", "串口距离值随传感器状态变化"],
    },
    {
        "id": "uno-servo-knob",
        "board": "arduino",
        "title": "08 · 电位器控制舵机",
        "summary": "把 ADC 值映射为 0-180 度舵机角度。",
        "difficulty": "进阶",
        "durationMinutes": 40,
        "tags": ["舵机", "PWM", "ADC", "执行器"],
        "knowledgePoints": ["Servo.attach", "map", "独立供电"],
        "sourceIds": ["arduino-examples", "wokwi-elements"],
        "code": """#include <Servo.h>
Servo arm;

void setup() {
  arm.attach(9);
}

void loop() {
  int angle = map(analogRead(A0), 0, 1023, 0, 180);
  arm.write(angle);
  delay(50);
}""",
        "parts": [
            _part("pot", "potentiometer", "角度旋钮", 190, 250, {"VCC": "5V", "OUT": "A0", "GND": "GND1"}, {"value": 512}),
            _part("servo", "servo", "SG90", 260, 90, {"SIG": "D9", "VCC": "5V", "GND": "GND2"}, {"angle": 90}),
        ],
        "acceptance": ["旋钮两端对应约 0 和 180 度", "信号使用 D9", "实板大负载使用独立 5V 并共地"],
    },
    {
        "id": "uno-dht-monitor",
        "board": "arduino",
        "title": "09 · 温湿度串口监测",
        "summary": "读取 DHT22 教学数据并进行串口观测。",
        "difficulty": "进阶",
        "durationMinutes": 35,
        "tags": ["DHT22", "温湿度", "单总线", "串口"],
        "knowledgePoints": ["数字传感器", "采样周期", "异常值检查"],
        "sourceIds": ["wokwi-elements"],
        "code": """void setup() {
  Serial.begin(9600);
}

void loop() {
  int humidity = dhtReadHumidity(2);
  int temperature = dhtReadTemperature(2);
  Serial.println(humidity);
  Serial.println(temperature);
  delay(1000);
}""",
        "parts": [
            _part("dht", "dht22", "DHT22", 210, 150, {"VCC": "5V", "DATA": "D2", "GND": "GND1"}, {"humidity": 58, "temperature": 24}),
            _part("serial", "serial-monitor", "串口终端", 70, 370, {"RX": "D1", "TX": "D0", "GND": "GND2"}),
        ],
        "acceptance": ["采样周期不少于 1 秒", "湿度和温度分别输出", "DATA 连接数字引脚"],
    },
    {
        "id": "uno-i2c-oled",
        "board": "arduino",
        "title": "10 · I2C OLED 状态显示",
        "summary": "确认 Uno 的 SDA/SCL 固定映射并显示传感器状态。",
        "difficulty": "进阶",
        "durationMinutes": 45,
        "tags": ["I2C", "OLED", "显示", "总线"],
        "knowledgePoints": ["SDA A4", "SCL A5", "I2C 地址"],
        "sourceIds": ["wokwi-elements"],
        "code": """void setup() {
  Serial.begin(9600);
  i2cDisplayBegin(0x3C);
}

void loop() {
  i2cDisplayText("MCU LAB READY");
  Serial.println("OLED 0x3C ready");
  delay(500);
}""",
        "parts": [
            _part("oled", "oled-i2c", "SSD1306", 205, 145, {"VCC": "5V", "GND": "GND1", "SDA": "A4", "SCL": "A5"}, {"text": "MCU LAB READY"}),
            _part("serial", "serial-monitor", "串口终端", 65, 370, {"RX": "D1", "TX": "D0", "GND": "GND2"}),
        ],
        "acceptance": ["SDA 必须连接 A4", "SCL 必须连接 A5", "默认地址 0x3C"],
    },
    {
        "id": "uno-relay-interlock",
        "board": "arduino",
        "title": "11 · 按键继电器联锁",
        "summary": "用低压逻辑验证执行器联锁，不模拟市电负载。",
        "difficulty": "综合",
        "durationMinutes": 45,
        "tags": ["继电器", "按键", "执行器", "安全"],
        "knowledgePoints": ["输出联锁", "低电平有效模块", "负载隔离"],
        "sourceIds": ["arduino-examples", "wokwi-elements"],
        "code": """void setup() {
  pinMode(2, INPUT_PULLUP);
  pinMode(7, OUTPUT);
}

void loop() {
  int pressed = digitalRead(2);
  digitalWrite(7, pressed == LOW ? HIGH : LOW);
  delay(50);
}""",
        "parts": [
            _part("button", "pushbutton", "使能按键", 205, 250, {"SIG": "D2", "GND": "GND1"}),
            _part("relay", "relay", "5V 继电器", 270, 95, {"VCC": "5V", "IN": "D7", "GND": "GND2"}),
        ],
        "acceptance": ["按住按键时继电器吸合", "松开后立即释放", "仿真和课堂实验均不得接入市电"],
    },
    {
        "id": "uno-blank",
        "board": "arduino",
        "title": "自定义 · 空白 Arduino 主板",
        "summary": "从完整 Uno 引脚和元件库开始自由搭建。",
        "difficulty": "自定义",
        "durationMinutes": 0,
        "tags": ["自由搭建", "Arduino"],
        "knowledgePoints": ["引脚规划", "接线检查"],
        "sourceIds": ["wokwi-elements", "avr8js"],
        "mode": "blank",
        "code": """void setup() {
  // 从元件库添加器件并连接端子
}

void loop() {
}""",
        "parts": [],
        "acceptance": ["所有必需端子完成接线", "虚拟烧录检查通过"],
    },
]


MCS51_EXPERIMENTS = [
    {
        "id": "8051-led-ready",
        "board": "8051",
        "title": "01 · P1 跑马灯",
        "summary": "观察累加器循环移位与 P1 端口输出。",
        "difficulty": "入门",
        "durationMinutes": 20,
        "tags": ["8051", "P1", "跑马灯", "移位"],
        "knowledgePoints": ["MOV", "RL", "SJMP", "准双向端口"],
        "sourceIds": ["learn-8051", "emu8051"],
        "code": """ORG 0000H
MOV A, #01H
LOOP:
  MOV P1, A
  RL A
  SJMP LOOP""",
        "parts": [
            _part(
                "p1-ledbar",
                "led-bar",
                "P1 LED Bar",
                180,
                125,
                {**{f"D{bit}": f"P1.{bit}" for bit in range(8)}, "COM": "GND"},
            ),
            _part("crystal", "crystal", "11.0592MHz", 175, 360, {"X1": "XTAL1", "X2": "XTAL2"}),
        ],
        "acceptance": ["单个亮点按位循环", "P1 各位均参与输出", "晶振连接 XTAL1/XTAL2"],
    },
    {
        "id": "8051-button-led",
        "board": "8051",
        "title": "02 · INT0 按键控制 LED",
        "summary": "使用 P3.2/INT0 作为低电平按键输入。",
        "difficulty": "基础",
        "durationMinutes": 25,
        "tags": ["8051", "按键", "INT0", "位寻址"],
        "knowledgePoints": ["JNB", "SETB", "CLR", "P3 复用功能"],
        "sourceIds": ["emu8051"],
        "code": """ORG 0000H
LOOP:
  JNB P3.2, PRESSED
  CLR P1.0
  SJMP LOOP
PRESSED:
  SETB P1.0
  SJMP LOOP""",
        "parts": [
            _part("button", "pushbutton", "P3.2 / INT0", 180, 245, {"SIG": "P3.2", "GND": "GND"}),
            _part("led", "led-module", "P1.0 LED", 210, 80, {"A": "P1.0", "K": "GND"}),
        ],
        "acceptance": ["按住时 P1.0 置位", "松开时 P1.0 清零", "按键连接 P3.2/INT0"],
    },
    {
        "id": "8051-seven-segment",
        "board": "8051",
        "title": "03 · 七段数码管计数",
        "summary": "用 P1 输出段码，理解共阴极段线映射。",
        "difficulty": "基础",
        "durationMinutes": 35,
        "tags": ["8051", "数码管", "段码", "查表"],
        "knowledgePoints": ["段码", "端口输出", "循环"],
        "sourceIds": ["learn-8051"],
        "code": """ORG 0000H
LOOP:
  MOV P1, #3FH
  ACALL DELAY
  MOV P1, #06H
  ACALL DELAY
  MOV P1, #5BH
  ACALL DELAY
  MOV P1, #4FH
  ACALL DELAY
  SJMP LOOP
DELAY:
  MOV R7, #20
D1:
  DJNZ R7, D1
  RET""",
        "parts": [
            _part(
                "seg",
                "seven-segment",
                "P1 数码管",
                180,
                120,
                {**{segment: f"P1.{index}" for index, segment in enumerate(["A", "B", "C", "D", "E", "F", "G", "DP"])}, "COM": "GND"},
            )
        ],
        "acceptance": ["数码管依次显示 0-3", "段线 A-DP 对应 P1.0-P1.7", "共阴端接地"],
    },
    {
        "id": "8051-traffic-light",
        "board": "8051",
        "title": "04 · P1 三色交通灯",
        "summary": "使用位操作和子程序组织交通灯状态。",
        "difficulty": "基础",
        "durationMinutes": 35,
        "tags": ["8051", "交通灯", "子程序", "位操作"],
        "knowledgePoints": ["SETB", "CLR", "ACALL", "RET"],
        "sourceIds": ["emu8051"],
        "code": """ORG 0000H
LOOP:
  SETB P1.0
  CLR P1.1
  CLR P1.2
  ACALL DELAY
  CLR P1.0
  SETB P1.1
  ACALL DELAY
  CLR P1.1
  SETB P1.2
  ACALL DELAY
  SJMP LOOP
DELAY:
  MOV R7, #30
D1:
  DJNZ R7, D1
  RET""",
        "parts": [
            _part("red", "led-module", "红灯", 165, 70, {"A": "P1.0", "K": "GND"}, {"color": "red"}),
            _part("yellow", "led-module", "黄灯", 165, 190, {"A": "P1.1", "K": "GND"}, {"color": "yellow"}),
            _part("green", "led-module", "绿灯", 165, 310, {"A": "P1.2", "K": "GND"}, {"color": "green"}),
        ],
        "acceptance": ["三路灯互斥", "子程序调用后正确返回", "位寻址不影响 P1 其他位"],
    },
    {
        "id": "8051-button-buzzer",
        "board": "8051",
        "title": "05 · 外部按键蜂鸣器",
        "summary": "通过 P3.3/INT1 输入控制 P1.7 蜂鸣器。",
        "difficulty": "进阶",
        "durationMinutes": 35,
        "tags": ["8051", "蜂鸣器", "INT1", "按键"],
        "knowledgePoints": ["JNB", "CPL", "低电平输入"],
        "sourceIds": ["emu8051"],
        "code": """ORG 0000H
LOOP:
  JNB P3.3, SOUND
  CLR P1.7
  SJMP LOOP
SOUND:
  CPL P1.7
  SJMP LOOP""",
        "parts": [
            _part("button", "pushbutton", "P3.3 / INT1", 175, 245, {"SIG": "P3.3", "GND": "GND"}),
            _part("buzzer", "buzzer", "P1.7 蜂鸣器", 210, 80, {"SIG": "P1.7", "GND": "GND"}),
        ],
        "acceptance": ["松开按键时蜂鸣器关闭", "按住时 P1.7 翻转", "输入使用 P3.3/INT1"],
    },
    {
        "id": "8051-ram-ready",
        "board": "8051",
        "title": "06 · 内部 RAM 寻址",
        "summary": "比较寄存器、直接寻址与 @R0 间接寻址。",
        "difficulty": "基础",
        "durationMinutes": 25,
        "tags": ["8051", "RAM", "寻址", "寄存器"],
        "knowledgePoints": ["@R0", "内部 RAM", "数据存储"],
        "sourceIds": ["learn-8051", "emu8051"],
        "code": """ORG 0000H
MOV R0, #30H
MOV A, #55H
MOV @R0, A
INC R0
MOV A, #0AAH
MOV @R0, A
SJMP $""",
        "parts": [],
        "acceptance": ["RAM[30H] 等于 55H", "RAM[31H] 等于 AAH", "R0 最终指向 31H"],
    },
    {
        "id": "8051-stack-ready",
        "board": "8051",
        "title": "07 · 堆栈 PUSH/POP",
        "summary": "观察 SP 增长方向和后进先出顺序。",
        "difficulty": "进阶",
        "durationMinutes": 30,
        "tags": ["8051", "堆栈", "PUSH", "POP", "SP"],
        "knowledgePoints": ["堆栈指针", "后进先出", "内部 RAM"],
        "sourceIds": ["learn-8051", "emu8051"],
        "code": """ORG 0000H
MOV SP, #30H
MOV A, #12H
PUSH ACC
MOV A, #34H
PUSH ACC
POP B
POP ACC
SJMP $""",
        "parts": [],
        "acceptance": ["B 最终等于 34H", "A 最终等于 12H", "SP 恢复到 30H"],
    },
    {
        "id": "8051-port-mirror",
        "board": "8051",
        "title": "08 · P3 输入镜像到 P1",
        "summary": "把八位输入端口镜像到 LED 灯条，理解端口读写。",
        "difficulty": "综合",
        "durationMinutes": 40,
        "tags": ["8051", "端口", "输入", "LED 灯条"],
        "knowledgePoints": ["MOV A,P3", "MOV P1,A", "准双向口"],
        "sourceIds": ["emu8051"],
        "code": """ORG 0000H
LOOP:
  MOV A, P3
  MOV P1, A
  SJMP LOOP""",
        "parts": [
            _part("button", "pushbutton", "P3.2 输入", 150, 300, {"SIG": "P3.2", "GND": "GND"}),
            _part(
                "bar",
                "led-bar",
                "P1 镜像",
                165,
                90,
                {**{f"D{bit}": f"P1.{bit}" for bit in range(8)}, "COM": "GND"},
            ),
        ],
        "acceptance": ["P3 状态变化会更新 P1", "P3.2 按下后对应灯位变化", "不使用 P0 避免开漏上拉歧义"],
    },
    {
        "id": "8051-blank",
        "board": "8051",
        "title": "自定义 · 空白 8051 主板",
        "summary": "从完整 40 引脚 AT89S52 和元件库开始搭建。",
        "difficulty": "自定义",
        "durationMinutes": 0,
        "tags": ["自由搭建", "8051"],
        "knowledgePoints": ["引脚复用", "端口规划", "接线检查"],
        "sourceIds": ["learn-8051", "emu8051"],
        "mode": "blank",
        "code": """ORG 0000H
; 添加元件并连接 P0-P3、晶振、电源和复位端子
NOP
SJMP $""",
        "parts": [],
        "acceptance": ["所有必需端子完成接线", "虚拟烧录检查通过"],
    },
]


MCU_EXPERIMENTS = ARDUINO_EXPERIMENTS + MCS51_EXPERIMENTS
BOARD_INDEX = {item["id"]: item for item in MCU_BOARDS}
COMPONENT_INDEX = {item["id"]: item for item in MCU_COMPONENTS}
EXPERIMENT_INDEX = {item["id"]: item for item in MCU_EXPERIMENTS}
SUPPORTED_MCU_PROJECTS = {
    board_id: {item["id"] for item in MCU_EXPERIMENTS if item["board"] == board_id}
    for board_id in BOARD_INDEX
}


def _experiment_payload(experiment: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(experiment)
    if item.get("steps"):
        return item
    part_names = []
    wiring = []
    for part in item.get("parts") or []:
        component = COMPONENT_INDEX.get(str(part.get("componentId") or "")) or {}
        label = str(part.get("label") or component.get("label") or part.get("componentId") or "元件")
        part_names.append(label)
        connections = part.get("connections") if isinstance(part.get("connections"), dict) else {}
        if connections:
            wiring.append(label + "：" + "、".join(f"{terminal}→{pin}" for terminal, pin in connections.items()))
    item["steps"] = [
        {
            "id": "goal",
            "title": "确认实验目标",
            "detail": str(item.get("summary") or "明确本次实验要验证的单片机行为。"),
        },
        {
            "id": "parts",
            "title": "准备实验元件",
            "detail": "、".join(part_names) if part_names else "从元件库选择本次实验需要的器件。",
        },
        {
            "id": "wiring",
            "title": "逐端子核对接线",
            "detail": "；".join(wiring) if wiring else "点击元件端子，再点击能力匹配的主板引脚完成接线。",
        },
        {
            "id": "flash",
            "title": "检查代码并虚拟烧录",
            "detail": "核对 " + "、".join(item.get("knowledgePoints") or ["代码入口", "引脚模式"]) + "，随后执行编译烧录检查。",
        },
        {
            "id": "verify",
            "title": "运行并逐项验收",
            "detail": "运行固件，操作画布中的输入元件，并对照验收项记录结果。",
            "checks": list(item.get("acceptance") or []),
        },
    ]
    return item


def get_mcu_board(board_id: object) -> dict[str, Any] | None:
    board = BOARD_INDEX.get(str(board_id or "").strip())
    return deepcopy(board) if board else None


def get_mcu_experiment(project_id: object) -> dict[str, Any] | None:
    experiment = EXPERIMENT_INDEX.get(str(project_id or "").strip())
    return _experiment_payload(experiment) if experiment else None


def mcu_catalog_payload(
    *,
    board: object = "",
    query: object = "",
    difficulty: object = "",
    component: object = "",
) -> dict[str, Any]:
    board_id = str(board or "").strip()
    query_text = str(query or "").strip().lower()
    difficulty_text = str(difficulty or "").strip()
    component_id = str(component or "").strip()
    experiments = []
    for experiment in MCU_EXPERIMENTS:
        if board_id and experiment["board"] != board_id:
            continue
        if difficulty_text and experiment.get("difficulty") != difficulty_text:
            continue
        if component_id and not any(part.get("componentId") == component_id for part in experiment.get("parts", [])):
            continue
        haystack = " ".join(
            [
                str(experiment.get("title") or ""),
                str(experiment.get("summary") or ""),
                " ".join(experiment.get("tags") or []),
                " ".join(experiment.get("knowledgePoints") or []),
            ]
        ).lower()
        if query_text and query_text not in haystack:
            continue
        experiments.append(_experiment_payload(experiment))
    return {
        "version": CATALOG_VERSION,
        "boards": deepcopy(MCU_BOARDS),
        "components": deepcopy(MCU_COMPONENTS),
        "experiments": experiments,
        "sources": deepcopy(OPEN_SOURCE_REFERENCES),
        "counts": {
            "boards": len(MCU_BOARDS),
            "components": len(MCU_COMPONENTS),
            "experiments": len(experiments),
        },
    }


def _search_text(*values: object) -> str:
    chunks = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            chunks.extend(str(item) for item in value)
        elif isinstance(value, dict):
            chunks.append(json.dumps(value, ensure_ascii=False))
        else:
            chunks.append(str(value or ""))
    return " ".join(chunks).lower()


def _context_matches_term(context: str, term: object) -> bool:
    normalized = str(term or "").strip().lower()
    if not normalized:
        return False
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]*", normalized):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", context))
    return normalized in context


def recommend_mcu_experiments(
    payload: dict[str, Any] | None = None,
    *,
    profile_context: object = "",
    history: list[dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    request_data = payload if isinstance(payload, dict) else {}
    requested_board = str(request_data.get("board") or "").strip().lower()
    board_aliases = {
        "arduino": "arduino",
        "uno": "arduino",
        "atmega328p": "arduino",
        "8051": "8051",
        "at89s52": "8051",
        "mcs-51": "8051",
        "mcs51": "8051",
    }
    requested_board_id = board_aliases.get(requested_board, "")
    preferred_difficulty = str(request_data.get("difficulty") or request_data.get("preferredDifficulty") or "").strip()
    exclude_completed = bool(request_data.get("excludeCompleted"))
    context = _search_text(request_data, profile_context)
    history_rows = history if isinstance(history, list) else []
    completed = {str(item.get("experiment_id") or item.get("experimentId") or "") for item in history_rows if item.get("passed")}
    eligible = [
        experiment
        for experiment in MCU_EXPERIMENTS
        if not requested_board_id or experiment["board"] == requested_board_id
    ]
    has_incomplete = any(experiment["id"] not in completed for experiment in eligible)

    scored = []
    for order, experiment in enumerate(MCU_EXPERIMENTS):
        if requested_board_id and experiment["board"] != requested_board_id:
            continue
        if exclude_completed and has_incomplete and experiment["id"] in completed:
            continue
        if experiment.get("mode") == "blank":
            base_score = -8
        else:
            base_score = max(0, 30 - order)
        reasons: list[str] = []
        if requested_board_id:
            base_score += 35
            reasons.append("匹配指定板卡")
        searchable_terms = list(experiment.get("tags") or []) + list(experiment.get("knowledgePoints") or [])
        matched_terms = [term for term in searchable_terms if len(term) >= 2 and _context_matches_term(context, term)]
        if matched_terms:
            base_score += min(48, 9 * len(set(matched_terms)))
            reasons.append("覆盖 " + "、".join(list(dict.fromkeys(matched_terms))[:3]))
        if preferred_difficulty and experiment.get("difficulty") == preferred_difficulty:
            base_score += 12
            reasons.append("符合期望难度")
        if experiment["id"] in completed:
            base_score -= 18
            reasons.append("已完成，可用于复习")
        else:
            base_score += 6
            reasons.append("尚未完成")
        scored.append((base_score, order, experiment, reasons))

    scored.sort(key=lambda item: (-item[0], item[1]))
    result = []
    for score, _order, experiment, reasons in scored[: max(1, min(int(limit or 5), 12))]:
        item = _experiment_payload(experiment)
        item["recommendation"] = {
            "score": max(0, int(score)),
            "reason": "；".join(reasons[:3]) or "按实验进阶顺序推荐",
        }
        result.append(item)
    return result


def _pin_accepts(pin: dict[str, Any], accepted: list[str]) -> bool:
    capabilities = set(pin.get("capabilities") or [])
    return bool(capabilities.intersection(accepted))


ARDUINO_ALLOWED_CALLS = {
    "setup",
    "loop",
    "pinMode",
    "digitalWrite",
    "digitalRead",
    "analogWrite",
    "analogRead",
    "delay",
    "delayMicroseconds",
    "map",
    "constrain",
    "tone",
    "noTone",
    "pulseIn",
    "dhtReadHumidity",
    "dhtReadTemperature",
    "i2cDisplayBegin",
    "i2cDisplayText",
}
MCS51_ALLOWED_OPS = {
    "MOV",
    "INC",
    "DEC",
    "RL",
    "RR",
    "RLC",
    "RRC",
    "SETB",
    "CLR",
    "CPL",
    "SJMP",
    "JMP",
    "LJMP",
    "AJMP",
    "JB",
    "JNB",
    "JC",
    "JNC",
    "JZ",
    "JNZ",
    "DJNZ",
    "CJNE",
    "ADD",
    "ADDC",
    "SUBB",
    "ANL",
    "ORL",
    "XRL",
    "PUSH",
    "POP",
    "ACALL",
    "LCALL",
    "RET",
    "NOP",
}


def _source_diagnostics(board_id: str, code: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if not code.strip():
        return [{"code": "EMPTY_SOURCE", "message": "代码不能为空"}], warnings
    if len(code.encode("utf-8")) > 48 * 1024:
        errors.append({"code": "SOURCE_TOO_LARGE", "message": "教学烧录代码不能超过 48KB"})
    if board_id == "arduino":
        if not re.search(r"\bvoid\s+setup\s*\(", code):
            errors.append({"code": "SETUP_MISSING", "message": "Arduino 程序缺少 void setup()"})
        if not re.search(r"\bvoid\s+loop\s*\(", code):
            errors.append({"code": "LOOP_MISSING", "message": "Arduino 程序缺少 void loop()"})
        calls = re.findall(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*\(", re.sub(r"//.*", "", code))
        unsupported = sorted(
            {
                call
                for call in calls
                if call not in ARDUINO_ALLOWED_CALLS
                and not call.startswith("Serial.")
                and not call.endswith(".attach")
                and not call.endswith(".write")
            }
        )
        if unsupported:
            errors.append(
                {
                    "code": "UNSUPPORTED_ARDUINO_CALL",
                    "message": "教学解释器暂不支持函数：" + "、".join(unsupported[:8]),
                }
            )
        errors.extend(_arduino_pin_usage_diagnostics(code))
    else:
        for line_no, source_line in enumerate(code.splitlines(), start=1):
            line = re.sub(r";.*", "", source_line).strip()
            if not line or re.match(r"^[A-Za-z_]\w*:\s*$", line):
                continue
            line = re.sub(r"^[A-Za-z_]\w*:\s*", "", line)
            if not line:
                continue
            op = line.split(None, 1)[0].upper()
            if op in {"ORG", "END", "DB"}:
                continue
            if op not in MCS51_ALLOWED_OPS:
                errors.append(
                    {
                        "code": "UNSUPPORTED_8051_OP",
                        "message": f"第 {line_no} 行指令 {op} 暂不受教学解释器支持",
                    }
                )
                if len(errors) >= 8:
                    break
    return errors, warnings


def _arduino_pin_usage_diagnostics(code: str) -> list[dict[str, str]]:
    """Validate statically resolvable Arduino API pin arguments against Uno capabilities."""
    board = BOARD_INDEX["arduino"]
    pin_index = {pin["id"]: pin for pin in board["pins"]}
    constants: dict[str, str] = {}
    cleaned = re.sub(r"/\*[\s\S]*?\*/", "", code)
    cleaned = re.sub(r"//.*", "", cleaned)
    for match in re.finditer(
        r"\b(?:const\s+)?(?:int|long|byte|uint8_t)\s+([A-Za-z_]\w*)\s*=\s*(A[0-5]|D?(?:[0-9]|1[0-3]))\s*;",
        cleaned,
    ):
        constants[match.group(1)] = match.group(2)
    for match in re.finditer(r"^\s*#define\s+([A-Za-z_]\w*)\s+(A[0-5]|D?(?:[0-9]|1[0-3]))\s*$", cleaned, re.MULTILINE):
        constants[match.group(1)] = match.group(2)

    def resolve_pin(expression: str, *, analog_numeric: bool = False) -> str:
        value = expression.strip().strip("()")
        value = constants.get(value, value).upper()
        if re.fullmatch(r"A[0-5]", value):
            return value
        if re.fullmatch(r"D(?:[0-9]|1[0-3])", value):
            return value
        if re.fullmatch(r"(?:[0-9]|1[0-3])", value):
            number = int(value)
            if analog_numeric and number <= 5:
                return f"A{number}"
            return f"D{number}"
        return ""

    checks: list[tuple[str, str, bool]] = [
        ("digitalWrite", "digital-output", False),
        ("digitalRead", "digital-input", False),
        ("analogWrite", "pwm", False),
        ("analogRead", "analog-input", True),
        ("tone", "digital-output", False),
        ("noTone", "digital-output", False),
        ("pulseIn", "digital-input", False),
    ]
    diagnostics: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    def validate_call(function_name: str, pin_id: str, capability: str) -> None:
        if not pin_id:
            return
        key = (function_name, pin_id, capability)
        if key in seen:
            return
        seen.add(key)
        pin = pin_index.get(pin_id)
        if not pin:
            diagnostics.append(
                {
                    "code": "SOURCE_PIN_UNKNOWN",
                    "message": f"{function_name} 使用了 Arduino Uno 不存在的引脚 {pin_id}",
                }
            )
            return
        if capability not in set(pin.get("capabilities") or []):
            diagnostics.append(
                {
                    "code": "SOURCE_PIN_CAPABILITY_MISMATCH",
                    "message": f"{function_name} 不能使用 {pin_id}：该引脚不具备 {capability} 能力",
                }
            )

    for function_name, capability, analog_numeric in checks:
        pattern = rf"\b{re.escape(function_name)}\s*\(\s*([^,\)]+)"
        for match in re.finditer(pattern, cleaned):
            validate_call(function_name, resolve_pin(match.group(1), analog_numeric=analog_numeric), capability)

    for match in re.finditer(
        r"\bpinMode\s*\(\s*([^,\)]+)\s*,\s*(INPUT_PULLUP|INPUT|OUTPUT)\s*\)",
        cleaned,
    ):
        capability = "digital-output" if match.group(2) == "OUTPUT" else "digital-input"
        validate_call("pinMode", resolve_pin(match.group(1)), capability)
    return diagnostics


def validate_mcu_flash(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    project_id = str(data.get("projectId") or data.get("project_id") or "").strip()
    experiment = EXPERIMENT_INDEX.get(project_id)
    board_id = str(data.get("board") or (experiment or {}).get("board") or "").strip()
    board = BOARD_INDEX.get(board_id)
    code = str(data.get("code") or (experiment or {}).get("code") or "")
    parts = data.get("parts") if isinstance(data.get("parts"), list) else deepcopy((experiment or {}).get("parts") or [])
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not board:
        errors.append({"code": "BOARD_UNSUPPORTED", "message": "不支持的单片机板卡"})
    else:
        source_errors, source_warnings = _source_diagnostics(board_id, code)
        errors.extend(source_errors)
        warnings.extend(source_warnings)
        pin_index = {pin["id"]: pin for pin in board["pins"]}
        output_drivers: dict[str, list[str]] = {}
        for part_index, part in enumerate(parts):
            component_id = str(part.get("componentId") or part.get("type") or "")
            component = COMPONENT_INDEX.get(component_id)
            label = str(part.get("label") or component_id or f"元件 {part_index + 1}")
            if not component:
                errors.append({"code": "COMPONENT_UNKNOWN", "message": f"{label} 不是受支持的元件"})
                continue
            connections = part.get("connections") if isinstance(part.get("connections"), dict) else {}
            legacy_pin = str(part.get("pin") or "").strip()
            if legacy_pin and component.get("terminals"):
                connections = {component["terminals"][0]["id"]: legacy_pin, **connections}
            for terminal in component.get("terminals", []):
                terminal_id = terminal["id"]
                board_pin_id = str(connections.get(terminal_id) or "").strip()
                if terminal.get("required") and not board_pin_id:
                    errors.append(
                        {
                            "code": "TERMINAL_UNCONNECTED",
                            "message": f"{label} 的 {terminal['label']} 端子未接线",
                        }
                    )
                    continue
                if not board_pin_id:
                    continue
                board_pin = pin_index.get(board_pin_id)
                if not board_pin:
                    errors.append(
                        {
                            "code": "PIN_UNKNOWN",
                            "message": f"{label}.{terminal['label']} 连接了不存在的引脚 {board_pin_id}",
                        }
                    )
                    continue
                accepts = list(terminal.get("accepts") or [])
                if accepts and not _pin_accepts(board_pin, accepts):
                    errors.append(
                        {
                            "code": "PIN_CAPABILITY_MISMATCH",
                            "message": f"{label}.{terminal['label']} 不能连接 {board_pin_id}（需要 {'/'.join(accepts)}）",
                        }
                    )
                if "digital-output" in accepts or "pwm" in accepts:
                    output_drivers.setdefault(board_pin_id, []).append(f"{label}.{terminal['label']}")
                if board_id == "8051" and "open-drain" in board_pin.get("capabilities", []) and (
                    "digital-output" in accepts or "pwm" in accepts
                ):
                    warnings.append(
                        {
                            "code": "P0_PULLUP_REQUIRED",
                            "message": f"{board_pin_id} 是开漏端口，实板作普通输出必须外接上拉电阻",
                        }
                    )
            if component_id == "servo":
                warnings.append(
                    {
                        "code": "SERVO_EXTERNAL_POWER",
                        "message": "舵机实板运行建议独立 5V 供电，并与主板共地",
                    }
                )

        for pin_id, drivers in output_drivers.items():
            if len(drivers) > 1:
                warnings.append(
                    {
                        "code": "SHARED_OUTPUT_PIN",
                        "message": f"{pin_id} 同时驱动 {'、'.join(drivers)}，请确认负载和逻辑意图",
                    }
                )

    canonical_parts = [
        {
            "id": str(part.get("id") or ""),
            "componentId": str(part.get("componentId") or part.get("type") or ""),
            "connections": part.get("connections") if isinstance(part.get("connections"), dict) else {},
        }
        for part in parts
    ]
    firmware_source = json.dumps(
        {"board": board_id, "projectId": project_id, "code": code, "parts": canonical_parts},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    firmware_id = "fw_" + hashlib.sha256(firmware_source).hexdigest()[:20]
    return {
        "valid": not errors,
        "board": board_id,
        "projectId": project_id,
        "firmware": {
            "id": firmware_id,
            "target": (board or {}).get("mcu") or board_id,
            "bytesEstimated": min(48 * 1024, max(64, len(code.encode("utf-8")) * 2)),
            "engine": "teaching-simulator",
            "status": "ready" if not errors else "rejected",
        },
        "diagnostics": {"errors": errors, "warnings": warnings},
        "simulationBoundary": (board or {}).get("simulationBoundary") or "",
    }


def normalize_mcu_resource_params(params: dict[str, Any] | None, context: str = "") -> dict[str, Any]:
    normalized = dict(params) if isinstance(params, dict) else {}
    requested_board = str(normalized.get("board") or "").strip()
    requested_project = str(normalized.get("projectId") or normalized.get("project_id") or "").strip()
    text = _search_text(
        context,
        requested_board,
        requested_project,
        normalized.get("topic"),
        normalized.get("targetTopic"),
        normalized.get("requirements"),
        normalized.get("learningGoal"),
        normalized.get("weakPoint"),
    )

    project_board = str((EXPERIMENT_INDEX.get(requested_project) or {}).get("board") or "")
    board_text = requested_board.lower()
    if project_board:
        board = project_board
    elif any(marker in board_text for marker in ["8051", "at89", "mcs-51", "mcs51"]):
        board = "8051"
    elif any(marker in board_text for marker in ["arduino", "uno", "atmega"]):
        board = "arduino"
    elif any(marker in text for marker in ["8051", "at89", "mcs-51", "mcs51", "汇编", "寻址", "堆栈"]):
        board = "8051"
    else:
        board = "arduino"

    if requested_project in SUPPORTED_MCU_PROJECTS[board]:
        project_id = requested_project
    else:
        semantic_routes = (
            [
                ("8051-stack-ready", ["stack", "堆栈", "push", "pop", "sp"]),
                ("8051-ram-ready", ["ram", "内存", "寻址", "存储"]),
                ("8051-seven-segment", ["seven", "7seg", "数码管", "段码"]),
                ("8051-button-buzzer", ["蜂鸣器", "buzzer", "int1"]),
                ("8051-button-led", ["button", "按键", "int0", "中断"]),
                ("8051-traffic-light", ["交通灯", "traffic", "状态机"]),
                ("8051-port-mirror", ["镜像", "端口输入", "port mirror"]),
            ]
            if board == "8051"
            else [
                ("uno-i2c-oled", ["i2c", "oled", "sda", "scl"]),
                ("uno-ultrasonic-distance", ["超声波", "ultrasonic", "hc-sr04", "测距"]),
                ("uno-servo-knob", ["舵机", "servo"]),
                ("uno-dht-monitor", ["dht", "温湿度"]),
                ("uno-relay-interlock", ["继电器", "relay", "联锁"]),
                ("uno-pwm-fade", ["pwm", "呼吸灯", "占空比"]),
                ("uno-pot-serial", ["adc", "电位器", "analogread", "模拟采样"]),
                ("uno-light-alarm", ["光敏", "ldr", "光照", "报警"]),
                ("uno-traffic-light", ["交通灯", "traffic", "状态机"]),
                ("uno-button-ready", ["button", "按键", "输入", "中断", "interrupt"]),
            ]
        )
        deterministic = next(
            (project for project, markers in semantic_routes if any(marker in text for marker in markers)),
            "",
        )
        if deterministic:
            project_id = deterministic
        else:
            recommendations = recommend_mcu_experiments({**normalized, "board": board, "topic": text}, limit=1)
            project_id = recommendations[0]["id"] if recommendations else ("8051-led-ready" if board == "8051" else "uno-led-ready")

    normalized.pop("project_id", None)
    normalized["board"] = board
    normalized["projectId"] = project_id
    if requested_board and board_text not in {"arduino", "8051"}:
        normalized["requestedBoard"] = requested_board[:80]
        normalized["simulatorAdaptation"] = (
            "当前教学模拟器未原生仿真该芯片，已映射到等效 GPIO/ADC/中断实验；"
            "芯片专有寄存器、时钟树和电气参数必须结合课程资料或实板复验。"
        )
    if requested_project and requested_project != project_id:
        normalized["requestedProjectId"] = requested_project[:120]
    return normalized


def normalize_mcu_route(route: str, params: dict[str, Any] | None = None, context: str = "") -> str:
    raw_route = str(route or "").strip()
    if not raw_route:
        return raw_route
    parsed = urlsplit(raw_route)
    marker = "/mcu-simulator"
    if marker not in parsed.path:
        return raw_route
    normalized = normalize_mcu_resource_params(params, context)
    prefix = parsed.path.split(marker, 1)[0] + marker
    path = f"{prefix}/{quote(str(normalized['board']))}/{quote(str(normalized['projectId']))}"
    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
