import cv2
import numpy as np
from mss import mss
import time
from datetime import datetime
import os
import sys

def check_installation():
    try:
        import cv2
        print(f"OpenCV версия: {cv2.__version__}")
    except:
        print("OpenCV не установлен")
        return False
    
    try:
        import mss
        print(f"MSS версия: {mss.__version__}")
    except:
        print("MSS не установлен")
        return False
    
    try:
        import numpy
        print(f"NumPy версия: {numpy.__version__}")
    except:
        print("NumPy не установлен")
        return False
    
    return True

def record_screen(output_name=None, duration=None, fps=60, monitor_index=1):

    if output_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"recording_{timestamp}.mp4"

    os.makedirs("recordings", exist_ok=True)
    output_path = os.path.join("recordings", output_name)
    
    with mss() as sct:
        if monitor_index >= len(sct.monitors):
            print(f"Монитор {monitor_index} не найден. Использую монитор 1")
            monitor_index = 1
            
        monitor = sct.monitors[monitor_index]
        
        width = monitor["width"]
        height = monitor["height"]
        
        print("="*50)
        print("ЗАПИСЬ ЭКРАНА")
        print("="*50)
        print(f"Монитор: {monitor_index}")
        print(f"Разрешение: {width}x{height}")
        print(f"FPS: {fps}")
        if duration:
            print(f"Длительность: {duration} сек")
        else:
            print(f"Длительность: до нажатия Ctrl+C")
        print(f"Файл: {output_path}")
        print("="*50)
        print("Запись началась...")
        print("")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_count = 0
        start_time = time.time()
        last_log = start_time
        
        try:
            while True:
                img = sct.grab(monitor)
                frame = np.array(img)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                out.write(frame)
                
                frame_count += 1
                current_time = time.time()

                if current_time - last_log >= 5:
                    elapsed = current_time - start_time
                    actual_fps = frame_count / elapsed
                    print(f"  Записано: {frame_count} кадров | Время: {elapsed:.1f}с | FPS: {actual_fps:.1f}")
                    last_log = current_time

                if duration and (current_time - start_time) >= duration:
                    print(f"\nДостигнута длительность {duration}с")
                    break
                
                time.sleep(1/fps)
                
        except KeyboardInterrupt:
            print("\n\nОстановка по запросу пользователя")
        
        finally:
            out.release()
            elapsed = time.time() - start_time
            actual_fps = frame_count / elapsed if elapsed > 0 else 0
            
            print("\n" + "="*50)
            print("ЗАПИСЬ ЗАВЕРШЕНА")
            print("="*50)
            print(f"Всего кадров: {frame_count}")
            print(f"Длительность: {elapsed:.1f} сек")
            print(f"Средний FPS: {actual_fps:.1f}")
            print(f"Файл: {output_path}")
            print("="*50)

def list_monitors():
    with mss() as sct:
        print("\nДоступные мониторы:")
        for i, monitor in enumerate(sct.monitors):
            if i == 0:
                print(f"  {i}: Все мониторы вместе")
            else:
                print(f"  {i}: {monitor['width']}x{monitor['height']}")

def main():

    if not check_installation():
        print("\nУстанови зависимости:")
        print("  pip install opencv-python mss numpy")
        sys.exit(1)
    
    print("\nЧто делаем?")
    print("1. Запись 60 секунд (1080p 60fps)")
    print("2. Запись до остановки (Ctrl+C)")
    print("3. Показать мониторы")
    print("4. Свои настройки")
    
    choice = input("\nВыбери (1-4): ").strip()
    
    if choice == "1":
        record_screen(
            output_name=f"recording_60s.mp4",
            duration=60,
            fps=60
        )
    
    elif choice == "2":
        record_screen(
            output_name=f"recording_infinite.mp4",
            duration=None,
            fps=60
        )
    
    elif choice == "3":
        list_monitors()
        mon = input("\nНомер монитора для записи [1]: ").strip()
        mon = int(mon) if mon else 1
        record_screen(
            monitor_index=mon,
            duration=None,
            fps=60
        )
    
    elif choice == "4":
        name = input("Имя файла [recording.mp4]: ").strip() or "recording.mp4"
        dur = input("Длительность в секундах (Enter - без огранич): ").strip()
        duration = int(dur) if dur else None
        fps = input("FPS [60]: ").strip()
        fps = int(fps) if fps else 60
        
        record_screen(
            output_name=name,
            duration=duration,
            fps=fps
        )
    
    else:
        print("Неверный выбор")

if __name__ == "__main__":
    main()
