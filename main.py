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
    except Exception:
        pass
save_to_db('/var/www/laboratoria.ru/static/style.css', 'text/css') 

def sweep_fixed_frequencies(fs=500, num_periods=1, freqs_to_test=None):
    if freqs_to_test is None:
        freqs_to_test = np.linspace(1, 30, 10)

    amplitudes = []
    phases = []

    for f in freqs_to_test:
        period = 1.0 / f
        duration = num_periods * period
        num_samples = int(fs * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        input_signal = np.sin(2 * np.pi * f * t)
        output_signal = []

        for val in input_signal:
            voltage = (val + 1) / 2 * 3.3
            try:
                DAC.DAC8532_Out_Voltage(0x30, voltage)
                time.sleep(0.001)
 
                ADC_Value = ADC.ADS1256_GetAll()
                measured_voltage = ADC_Value[4] * 5.0 / 0x7fffff
                output_signal.append(measured_voltage)
            except Exception:
                break

        output_signal = np.array(output_signal)
        ref_cos = np.cos(2 * np.pi * f * t)
        ref_sin = np.sin(2 * np.pi * f * t)

        I = 2 * np.mean(output_signal * ref_cos)
        Q = 2 * np.mean(output_signal * ref_sin)
        amp = np.sqrt(I**2 + Q**2)
        phase = np.arctan2(Q, I)
        amp_db = 20 * np.log10(amp + 1e-8)
        phase_deg = 90 - np.abs(np.degrees(phase) % 90)



        amplitudes.append(amp_db)
        phases.append(phase_deg)

    DAC.DAC8532_Out_Voltage(0x30, 0)
    return freqs_to_test, amplitudes, phases


def measure_step_response(fs=500, duration=1.0, step_voltage=3.3):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    response = []

    step_start = int(0.1 * fs)  
    step_end = int(0.2 * fs)    

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
       # time.sleep(1.0 / fs)

    DAC.DAC8532_Out_Voltage(0x30, 0)
    return t, np.array(response)


def plot_bode(freqs, amps_db, phases_deg):
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

    freq_min, freq_max = 0, max(freqs) * 1.1
    amp_min = max(min(amps_db) - 5, -100)
    amp_max = min(max(amps_db) + 5, 5)
    phase_min = 0
    phase_max = 90
    phase_padding = 5

    try:
        plt.figure(figsize=(10, 6))
        plt.plot(freqs, amps_db, 'r-o', label='Амплитуда (дБ)')
        plt.title("АЧХ (амплитудно-частотная характеристика)")
        plt.xlabel("Частота (Гц)")
        plt.ylabel("Амплитуда (дБ)")
        plt.xlim(1, 30)
        plt.ylim(amp_min, amp_max+2)
        plt.grid(True)
        plt.legend()
        amplitude_path = f"{image_dir}/amplitude.jpg"
        plt.savefig(amplitude_path)
        plt.close()
    except Exception:
        pass

    try:
        plt.figure(figsize=(10, 6))
        plt.plot(freqs, phases_deg, 'b-o', label='Фаза (градусы)')
        plt.title("ФЧХ (фазо-частотная характеристика)")
        plt.xlabel("Частота (Гц)")
        plt.ylabel("Фаза (градусы)")
        plt.xlim(1, 30)
        plt.ylim(phase_min - phase_padding, phase_max + phase_padding)
        plt.grid(True)
        plt.legend()
        phase_path = f"{image_dir}/phase.jpg"
        plt.savefig(phase_path)
        plt.close()
    except Exception:
        pass

    save_to_db(amplitude_path, "image/jpeg")
    save_to_db(phase_path, "image/jpeg")



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
    except Exception:
        pass
    finally:
        DAC.DAC8532_Out_Voltage(0x30, 0)
        GPIO.cleanup()


