import os
import requests
import time
import random
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pymongo import MongoClient

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

#from background import keep_alive 

#keep_alive()

# ----- Конфигурация MongoDB -----
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://netcool322:3fMlxrHb7cCYj5S3@cluster0.z21jj.mongodb.net/')
client = MongoClient(MONGO_URI)
db = client['pinterest_bot']
downloaded_posts_collection = db['downloaded_posts']
settings_collection = db['settings']  # Новая коллекция для хранения настроек

# Функция для получения времени последнего скачивания
def get_last_download_time():
    last_download = settings_collection.find_one({'name': 'last_download_time'})
    return last_download['value'] if last_download else 0  # Вернем 0, если не найдено

# Функция для обновления времени последнего скачивания
def update_last_download_time(timestamp):
    settings_collection.update_one(
        {'name': 'last_download_time'},
        {'$set': {'value': timestamp}},
        upsert=True  # Создайте новую запись, если она не существует
    )

#os.system("wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb")
#os.system("sudo apt install ./google-chrome-stable_current_amd64.deb")

# ----- Конфигурация для Pinterest -----
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")  # Отключение GPU
chrome_options.add_argument("--window-size=1920x1080")

#driver = webdriver.Chrome(options=chrome_options)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

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
    driver.get('https://www.pinterest.com')
    time.sleep(3)

    with open('cookies.json', 'r') as f:
        cookies = json.load(f)
        for cookie in cookies:
            try:
                if 'name' in cookie and 'value' in cookie and 'domain' in cookie:
                    driver.add_cookie(cookie)
            except Exception as e:
                print(f"Ошибка при добавлении куки: {e}")

    driver.get('https://www.pinterest.com')
    time.sleep(5)
    if "login" not in driver.current_url:
        print("Авторизация по кукам успешна!")
    else:
        print("Ошибка авторизации по кукам!")

def is_post_downloaded(pin_id):
    return downloaded_posts_collection.find_one({'pin_id': pin_id}) is not None

def save_downloaded_post(pin_id):
    post_data = {'pin_id': pin_id, 'timestamp': time.time()}
    downloaded_posts_collection.insert_one(post_data)

def download_images_from_pinterest(profile_name):
    profile_name = profile_name.upper()  # Приводим имя профиля к верхнему регистру
    driver.get(f'https://www.pinterest.com/{profile_name}/_created/')
    time.sleep(5)

    downloaded_count = 0
    previous_height = driver.execute_script("return document.body.scrollHeight")

    # Прокручиваем страницу, чтобы первые 10 постов были загружены
    for _ in range(0):  # Прокрутка несколько раз, чтобы загрузить больше пинов
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Задержка для подгрузки пинов
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == previous_height:
            break
        previous_height = new_height

    # Ищем все элементы изображений
    image_elements = driver.find_elements(By.XPATH, '//img[@class="hCL kVc L4E MIw"]')

    for img in image_elements:
        if downloaded_count >= 10:
            break

        pin_src = img.get_attribute('src')
        pin_alt = img.get_attribute('alt')

        # Генерация уникального ID пина
        pin_id = pin_src.split('/')[-1].split('.')[0]

        # Фильтрация изображений профиля или уже загруженных пинов
        if (pin_alt == profile_name or pin_alt == profile_name.upper() or
            pin_alt == "Изображение обложки профиля" or 
            pin_alt == "User Avatar" or  pin_alt == "" or
            is_post_downloaded(pin_id)):
            continue

        image_url = img.get_attribute('src')
        image_path = f"ReadyImage/{profile_name}_{pin_id}.jpg"

        # Скачиваем изображение
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(image_path, 'wb') as img_file:
                img_file.write(response.content)
            print(f"Изображение {pin_id} скачано.")
            save_downloaded_post(pin_id)
            downloaded_count += 1
        else:
            print(f"Ошибка при загрузке изображения {pin_id}: {response.status_code}")

        time.sleep(random.uniform(2, 5))

    print(f"Всего скачано {downloaded_count} изображений для профиля {profile_name}.")

# Функция для публикации пина
def post_pin(image_path, link):
    print("Переходим на страницу создания пина...")
    driver.get('https://ru.pinterest.com/pin-creation-tool/')
    time.sleep(5)

    print("Загружаем изображение...")
    try:
        upload_input = driver.find_element(By.XPATH, '//input[@type="file"]')
        upload_input.send_keys(image_path)
        time.sleep(5)
        print("Изображение загружено.")
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return

    # Вводим ссылку
    print("Вводим ссылку...")
    try:
        link_input = driver.find_element(By.XPATH, '//input[@placeholder="Добавить ссылку"]')
        link_input.send_keys(link)
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

def delete_image(image_path):
    if os.path.exists(image_path):
        os.remove(image_path)
        print(f"Изображение {image_path} удалено.")

# Основной цикл
if __name__ == "__main__":
    #keep_alive()
    #login_with_cookies()
    email = "n3tcool@yandex.ru"
    password = "@Busing1234"
    login_to_pinterest(email, password)

    profiles = []
    with open('profiles.txt', 'r') as f:
        profiles = [line.strip() for line in f if line.strip()]

    last_download_time = get_last_download_time()  # Получаем время из базы данных
    print("last_download_time = ", last_download_time)

    while True:
        current_time = time.time()

        # Проверка, прошло ли 24 часа с последнего скачивания
        if current_time - last_download_time >= 86400:  # 24 часа
            print("Переходим к скачиванию изображений...")
            for profile in profiles:
                download_images_from_pinterest(profile)
            last_download_time = current_time

        # Проверка наличия изображений для публикации
        image_files = os.listdir('ReadyImage')
        if image_files:
            print("Переходим к публикации изображений...")
            for image_file in image_files:
                #image_path = os.path.join('/workspaces/PinterestAutoPoste/ReadyImage/', image_file)
                image_path = "/workspaces/PinterestAutoPoster/ReadyImage/" + image_file
                link = "https://t.me/fyefye"
                if os.path.exists(image_path):
                    post_pin(image_path, link)
                    delete_image(image_path)
                print("Уходим в сон на 1 час...")
                time.sleep(3600)  # Уходим в сон на 1 час
                break  # После публикации одного пина выходим из цикла
        else:
            print("Нет изображений для публикации, проверяем снова через 60 секунд.")
            time.sleep(60)  # Проверяем каждую минуту
