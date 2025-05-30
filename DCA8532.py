import spidev
import RPi.GPIO as GPIO

channel_A = 0x30
channel_B = 0x34
DAC_Value_MAX = 65535
DAC_VREF = 3.3

class DAC8532:
    def __init__(self):
        # Создаём свой SPI-объект для ЦАП с device=1 (CE1)
        self.spi = spidev.SpiDev()
        self.spi.open(0, 1)  # Изменяем только цифру: bus=0, device=1 (CE1)
        self.spi.max_speed_hz = 1000000  # Скорость SPI
        self.spi.mode = 0b01  # Режим SPI для ЦАП

    def DAC8532_Write_Data(self, Channel, Data):
        self.spi.xfer2([Channel, Data >> 8, Data & 0xff])

    def DAC8532_Out_Voltage(self, Channel, Voltage):
        if 0 <= Voltage <= DAC_VREF:
            temp = int(Voltage * DAC_Value_MAX / DAC_VREF)
            self.DAC8532_Write_Data(Channel, temp)

    def close(self):
        self.spi.close()
