from selenium import webdriver
from selenium.webdriver.common.by import By

# Настройки браузера (используем Chrome)
options = webdriver.ChromeOptions()
options.add_argument('--headless')  # Запуск браузера в фоновом режиме

# Создание экземпляра браузера
driver = webdriver.Chrome(options=options)

# Открытие страницы Google
driver.get('https://www.google.com')

# Проверка наличия элемента с текстом "Google"
try:
    element = driver.find_element(By.NAME, 'q')  # Поле ввода поиска
    print("Страница Google успешно загружена.")
except:
    print("Не удалось загрузить страницу Google.")

# Закрытие браузера
driver.quit()
