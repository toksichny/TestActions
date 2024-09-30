import os
import random
import time
import json
import requests
from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----- Конфигурация MongoDB -----
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://netcool322:3fMlxrHb7cCYj5S3@cluster0.z21jj.mongodb.net/')
client = MongoClient(MONGO_URI)
db = client['pinterest_bot']
downloaded_posts_collection = db['downloaded_posts']

# ----- Конфигурация для Pinterest -----
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
#driver = webdriver.Chrome(options=chrome_options)

# Функция для авторизации на Pinterest
def login_to_pinterest(email, password):
    print("Переходим на страницу логина...")
    driver.get('https://www.pinterest.com/login/')
    time.sleep(3)
    
    print("Вводим данные для авторизации...")
    email_input = driver.find_element(By.NAME, 'id')
    password_input = driver.find_element(By.NAME, 'password')
    
    email_input.send_keys(email)
    password_input.send_keys(password)
    
    password_input.send_keys(Keys.RETURN)
    time.sleep(5)

    # Проверка успешного входа
    if "login" not in driver.current_url:
        print("Авторизация прошла успешно!")
    else:
        print("Ошибка авторизации, проверьте логин или пароль.")

def login_with_cookies():
    print("Логинимся в Pinterest по кукам...")
    
    # Переход на главную страницу Pinterest для установки куков
    driver.get('https://www.pinterest.com')
    time.sleep(3)

    with open('cookies.json', 'r') as f:
        cookies = json.load(f)
        for cookie in cookies:
            try:
                # Создаем словарь куки с проверкой на корректность 'expiry'
                cookie_dict = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': '.pinterest.com',  # Убедитесь, что домен правильный
                    'path': cookie.get('path', '/')
                }

                # Убираем поле 'expiry', если оно некорректно
                if 'expiry' in cookie and isinstance(cookie['expiry'], (int, float)):
                    cookie_dict['expiry'] = cookie['expiry']
                
                # Добавляем куки в драйвер
                driver.add_cookie(cookie_dict)
            except Exception as e:
                print(f"Ошибка при добавлении куки: {e}")

    # Переход на главную страницу после установки куков
    driver.get('https://www.pinterest.com')
    time.sleep(5)

    # Проверка успешного входа
    if "login" not in driver.current_url:
        print("Авторизация по кукам успешна!")
    else:
        print("Ошибка авторизации по кукам! Проверьте правильность куков.")

def is_post_downloaded(pin_id):
    return downloaded_posts_collection.find_one({'pin_id': pin_id}) is not None

def save_downloaded_post(pin_id):
    downloaded_posts_collection.insert_one({'pin_id': pin_id, 'timestamp': time.time()})

def download_random_image(profile_name):
    driver.get(f'https://www.pinterest.com/{profile_name}/_created/')
    time.sleep(10)  # Увеличил время ожидания

    image_elements = driver.find_elements(By.XPATH, '//img[@class="hCL kVc L4E MIw"]')
    
    downloaded_images = 0
    for img in image_elements[:10]:  # Только первые 10 изображений
        pin_srcset = img.get_attribute('srcset')  # Используем srcset для более высокого разрешения
        if pin_srcset:
            pin_src = pin_srcset.split(',')[-1].split(' ')[0]  # Берем версию с наибольшим разрешением
        else:
            pin_src = img.get_attribute('src')

        pin_id = pin_src.split('/')[-1].split('.')[0]
        pin_alt = img.get_attribute('alt')
        # Фильтрация изображений профиля или уже загруженных пинов
        if (pin_alt == profile_name or pin_alt == profile_name.upper() or
            pin_alt == "Изображение обложки профиля" or 
            pin_alt == "User Avatar" or  pin_alt == "" or
            is_post_downloaded(pin_id)):
            continue

        if not is_post_downloaded(pin_id):
            save_downloaded_post(pin_id)
            return pin_src, pin_id

        downloaded_images += 1

    if downloaded_images == 10:
        print(f"Все 10 изображений профиля {profile_name} уже скачаны.")
        return None, None
    return None, None 

def post_pin(image_url):
    driver.get('https://ru.pinterest.com/pin-creation-tool/')
    time.sleep(5)
    upload_input = driver.find_element(By.XPATH, '//input[@type="file"]')
    response = requests.get(image_url)
    
    with open('temp_image.jpg', 'wb') as img_file:
        img_file.write(response.content)
    
   
    print("Загружаем изображение...")
    try:
        upload_input.send_keys(os.path.abspath('temp_image.jpg'))
        time.sleep(5)
        print("Изображение загружено.")
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return

    # Вводим ссылку
    print("Вводим ссылку...")
    try:
        link_input = driver.find_element(By.XPATH, '//input[@placeholder="Добавить ссылку"]')
        link_input.send_keys('https://t.me/fyefye')
        print("Ссылка введена.")
    except Exception as e:
        print(f"Ошибка при вводе ссылки: {e}")
    
    # Подтверждаем публикацию
    print("Публикуем пин...")
    try:
        publish_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//div[contains(text(), "Опубликовать")]]'))
        )
        if publish_button.is_enabled():
            print("Кнопка 'Опубликовать' активна, кликаем по ней...")
            publish_button.click()
            time.sleep(5)
        else:
            print("Кнопка 'Опубликовать' не активна. Возможно, не все данные заполнены.")
    except Exception as e:
        print(f"Ошибка при публикации пина: {e}")

    try:
        publish_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[.//div[contains(text(), "Опубликовать")]]'))
        )
        if publish_button.is_enabled():
            print("Кнопка 'Опубликовать' активна, кликаем по ней...")
            publish_button.click()
            time.sleep(5)
        else:
            print("Кнопка 'Опубликовать' не активна. Возможно, не все данные заполнены.")
    except Exception as e:
        print(f"Ошибка при публикации пина: {e}")
      
    time.sleep(10)
    # Проверка публикации пина
    if "pin" in driver.current_url:
        print("Пин успешно опубликован.")
    else:
        print("Публикация пина не удалась.")

if __name__ == "__main__":
    email = "vintagefellow22@gmail.com"
    password = "@Busing1234"
    #login_to_pinterest(email, password)
    login_with_cookies()

    profiles = []
    with open('profiles.txt', 'r') as f:
        profiles = [line.strip() for line in f if line.strip()]

    while profiles:
        random_profile = random.choice(profiles)
        try:
            image_url, pin_id = download_random_image(random_profile)
        
            if image_url:
                post_pin(image_url)
                break
            else:
                print(f"Изображения для профиля {random_profile} уже скачаны.")
                profiles.remove(random_profile)
    
        except Exception as e:
            print(f"Произошла ошибка при обработке профиля {random_profile}: {e}")
            profiles.remove(random_profile)  # Удаляем профиль из списка при ошибке
