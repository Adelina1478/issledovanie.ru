import time
import ADS1256
import DAC8532
import RPi.GPIO as GPIO
import numpy as np
import matplotlib.pyplot as plt
import os
import sqlite3

def save_to_db(path, filetype):
    try:
        if not os.path.exists(path):
            return
        with open(path, 'rb') as f:
            content = f.read()
        conn = sqlite3.connect('/var/www/laboratoria.ru/database.db', timeout=10)
        c = conn.cursor()
        c.execute('''
            INSERT INTO files (filename, filetype, content)
            VALUES (?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                filetype=excluded.filetype,
                content=excluded.content
        ''', (os.path.basename(path), filetype, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")

save_to_db('/var/www/laboratoria.ru/static/style.css', 'text/css') 

def sweep_fixed_frequencies(fs=1000, duration=1.0, freqs_to_test=None):
    if freqs_to_test is None:
        freqs_to_test = np.linspace(0, 65, 10)

    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    amplitudes = []
    phases = []

    for f in freqs_to_test:
        input_signal = np.sin(2 * np.pi * f * t)
        output_signal = []

        for i, val in enumerate(input_signal):
            voltage = (val + 1) / 2 * 3.3
            try:
                DAC.DAC8532_Out_Voltage(0x30, voltage)
                time.sleep(0.001)
                ADC_Value = ADC.ADS1256_GetAll()
                measured_voltage = ADC_Value[4] * 5.0 / 0x7fffff
                output_signal.append(measured_voltage)
            except Exception as e:
                print(f"Ошибка при обработке сигнала на частоте {f} Гц: {e}")
                break
        
        output_signal = np.array(output_signal)
        ref_cos = np.cos(2 * np.pi * f * t)
        ref_sin = np.sin(2 * np.pi * f * t)

        I = 2 * np.mean(output_signal * ref_cos)
        Q = 2 * np.mean(output_signal * ref_sin)
        amp = np.sqrt(I**2 + Q**2)
        # Исправлено вычисление фазы
        phase = -np.arctan2(-I, Q)  # Корректный расчет фазового сдвига
        amp_db = 20 * np.log10(amp + 1e-8)

        phase_deg = np.degrees(phase)
        print(f"Частота: {f:.2f} Гц, Амплитуда (дБ): {amp_db:.2f}, Фаза (градусы): {phase_deg:.2f}")

        amplitudes.append(amp_db)
        phases.append(phase_deg)

    # Убрана нормализация, так как фаза уже корректна
    phases = np.unwrap(np.radians(phases))
    phases = np.degrees(phases)

    DAC.DAC8532_Out_Voltage(0x30, 0)
    return freqs_to_test, amplitudes, phases

def plot_bode(freqs, amps_db, phases_deg):
    image_dir = "/var/www/laboratoria.ru/images"
    fallback_dir = os.path.expanduser("~/plots")

    try:
        os.makedirs(image_dir, exist_ok=True)
        if not os.access(image_dir, os.W_OK):
            image_dir = fallback_dir
            os.makedirs(image_dir, exist_ok=True)
    except Exception as e:
        print(f"Ошибка при создании директории: {e}")
        image_dir = fallback_dir
        os.makedirs(image_dir, exist_ok=True)

    # Установка диапазона для фазы от 0 до -90
    phase_min = -90
    phase_max = 0
    phase_padding = 5

    # Построение АЧХ
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(freqs, amps_db, 'r-o', label='Амплитуда (дБ)')
        plt.title("АЧХ")
        plt.xlabel("Частота (Гц)")
        plt.ylabel("Амплитуда (дБ)")
        plt.grid(True)
        amplitude_path = f"{image_dir}/sweep_amplitude.jpg"
        plt.savefig(amplitude_path)
        plt.close()
    except Exception as e:
        print(f"Ошибка при сохранении АЧХ: {e}")

    # Построение ФЧХ с исправленным диапазоном
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(freqs, phases_deg, 'b-o', label='Фаза (градусы)')
        plt.title("ФЧХ")
        plt.xlabel("Частота (Гц)")
        plt.ylabel("Фаза (градусы)")
        plt.ylim(phase_min - phase_padding, phase_max + phase_padding)
        plt.grid(True)
        phase_path = f"{image_dir}/sweep_phase.jpg"
        plt.savefig(phase_path)
        plt.close()
    except Exception as e:
        print(f"Ошибка при сохранении ФЧХ: {e}")

    save_to_db(amplitude_path, "image/jpeg")
    save_to_db(phase_path, "image/jpeg")

def measure_step_response(fs=1000, duration=1.0, step_voltage=3.3):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    response = []

    step_start = int(0.2 * fs)  # шаг начинается после 200 мс
    step_end = int(0.7 * fs)    # шаг длится до 700 мс (500 мс шаг)

    for i in range(len(t)):
        if i < step_start:
            DAC.DAC8532_Out_Voltage(0x30, 0)  # начальный 0 В
        elif i < step_end:
            DAC.DAC8532_Out_Voltage(0x30, step_voltage)  # шаг на 3.3 В
        else:
            DAC.DAC8532_Out_Voltage(0x30, 0)  # возврат к 0 В

        try:
            ADC_Value = ADC.ADS1256_GetAll()
            measured_voltage = ADC_Value[4] * 5.0 / 0x7fffff
            response.append(measured_voltage)
        except Exception:
            response.append(0)  # на случай ошибки – запишем 0
        time.sleep(1.0 / fs)

    DAC.DAC8532_Out_Voltage(0x30, 0)
    return t, np.array(response)


def plot_step_response(t, response):
    image_dir = "/var/www/laboratoria.ru/images"
    fallback_dir = os.path.expanduser("~/plots")

    try:
        os.makedirs(image_dir, exist_ok=True)
        if not os.access(image_dir, os.W_OK):
            image_dir = fallback_dir
            os.makedirs(image_dir, exist_ok=True)
    except Exception:
        image_dir = fallback_dir
        os.makedirs(image_dir, exist_ok=True)

    try:
        plt.figure(figsize=(10, 5))
        plt.plot(t, response, 'g')
        plt.title("Переходная характеристика")
        plt.xlabel("Время (с)")
        plt.ylabel("Выходное напряжение (В)")
        plt.grid(True)
        step_path = f"{image_dir}/graph.jpg"
        plt.savefig(step_path)
        plt.close()
        save_to_db(step_path, "image/jpeg")
    except Exception:
        pass


if __name__ == "__main__":
    ADC = ADS1256.ADS1256()
    DAC = DAC8532.DAC8532()

    try:
        ADC.ADS1256_init()
        freqs, amps, phases = sweep_fixed_frequencies()
        plot_bode(freqs, amps, phases)
        
        t, step = measure_step_response()
        plot_step_response(t, step)
    except Exception as e:
        print(f"Ошибка в основном блоке: {e}")
    finally:
        DAC.DAC8532_Out_Voltage(0x30, 0)
        GPIO.cleanup()
