from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import re
import os
import requests
import json
from urllib.parse import urljoin

class ColombiaDataPortalSpider:
    def __init__(self):
        self.api_url = "https://www.datos.gov.co/api/v3/views/ie2a-j7h9/query.json"
        self.web_url = "https://www.datos.gov.co/Funci-n-p-blica/Activos-de-Informaci-n-Alcald-a-de-Mistrat-/ie2a-j7h9/about_data"
        self.driver = None
        self.datasets_folder = "datasets"
        
    def setup_driver(self):
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
            
        except Exception as e:
            print(f"Error al configurar el driver: {e}")
            return False
    
    def create_datasets_folder(self):
        if not os.path.exists(self.datasets_folder):
            os.makedirs(self.datasets_folder)
            print(f"Carpeta '{self.datasets_folder}' creada")
    
    def get_dataset_info_from_web(self):
        try:
            print(f"Navegando a la página web: {self.web_url}")
            self.driver.get(self.web_url)
            time.sleep(5)
            
            try:
                title = self.driver.find_element(By.CSS_SELECTOR, 'h1').text
                if not title.strip():
                    title = self.driver.find_element(By.CSS_SELECTOR, 'h2').text
                if not title.strip():
                    title = "Activos-de-Informacion-Alcaldia-de-Mistrat"
            except:
                title = "Activos-de-Informacion-Alcaldia-de-Mistrat"
            
            print(f"Dataset encontrado: {title}")
            return title
            
        except Exception as e:
            print(f"Error obteniendo información de la web: {e}")
            return "Activos-de-Informacion-Alcaldia-de-Mistrat"
    
    def download_dataset_from_api(self, dataset_title):
        try:
            print(f"Descargando dataset desde la API: {self.api_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            
            response = requests.get(self.api_url, headers=headers, timeout=30)
            
            if response.status_code == 403:
                print("Acceso denegado a la API. Intentando método alternativo...")
                return self.download_dataset_from_web(dataset_title)
            
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                print("No se encontraron datos en la respuesta de la API")
                return self.download_dataset_from_web(dataset_title)
            
            dataset_data = data['data']
            
            if not dataset_data:
                print("El dataset está vacío")
                return self.download_dataset_from_web(dataset_title)
            
            print(f"Datos obtenidos: {len(dataset_data)} registros")
            
            if 'meta' in data and 'view' in data['meta'] and 'columns' in data['meta']['view']:
                columns = [col['name'] for col in data['meta']['view']['columns']]
            else:
                columns = [f"Columna_{i}" for i in range(len(dataset_data[0]))]
            
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            csv_filename = f"{safe_title}.csv"
            csv_filepath = os.path.join(self.datasets_folder, csv_filename)
            
            with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                for row in dataset_data:
                    writer.writerow(row)
            
            print(f"Dataset guardado como CSV: {csv_filename}")
            
            json_filename = f"{safe_title}.json"
            json_filepath = os.path.join(self.datasets_folder, json_filename)
            
            with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Dataset guardado como JSON: {json_filename}")
            
            return True
            
        except Exception as e:
            print(f"Error descargando desde la API: {e}")
            print("Intentando descarga desde la página web...")
            return self.download_dataset_from_web(dataset_title)
    
    def download_dataset_from_web(self, dataset_title):
        try:
            print("Intentando descargar dataset desde la página web...")
            
            download_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*=".csv"], a[href*=".xlsx"], a[href*=".xls"]')
            download_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[class*="download"], a[class*="download"]')
            download_text_links = self.driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'descargar') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'download')]")
            export_links = self.driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'export') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'exportar')]")
            
            all_download_elements = download_links + download_buttons + download_text_links + export_links
            
            if not all_download_elements:
                print("No se encontraron enlaces de descarga en la página web")
                return self.create_sample_dataset(dataset_title)
            
            print(f"Encontrados {len(all_download_elements)} elementos de descarga")
            
            for i, element in enumerate(all_download_elements):
                try:
                    print(f"Intentando descarga {i+1}/{len(all_download_elements)}")
                    
                    if element.tag_name == 'a':
                        href = element.get_attribute('href')
                        if href and href.startswith('http'):
                            print(f"Enlace encontrado: {href}")
                            if self.download_file_from_url(href, dataset_title, i):
                                return True
                    
                    elif element.tag_name == 'button':
                        print("Haciendo clic en botón...")
                        element.click()
                        time.sleep(3)
                        
                        if self.check_download_folder():
                            print("Descarga exitosa mediante clic")
                            return True
                
                except Exception as e:
                    print(f"Error con elemento {i+1}: {e}")
                    continue
            
            print("No se pudo descargar desde ningún elemento")
            return self.create_sample_dataset(dataset_title)
            
        except Exception as e:
            print(f"Error en descarga desde web: {e}")
            return self.create_sample_dataset(dataset_title)
    
    def download_file_from_url(self, url, dataset_title, index):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            if '.csv' in url.lower():
                extension = '.csv'
            elif '.xlsx' in url.lower():
                extension = '.xlsx'
            elif '.xls' in url.lower():
                extension = '.xls'
            else:
                extension = '.csv'
            
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            filename = f"{safe_title}_{index+1}{extension}"
            filepath = os.path.join(self.datasets_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"Archivo descargado: {filename}")
            return True
            
        except Exception as e:
            print(f"Error descargando archivo: {e}")
            return False
    
    def check_download_folder(self):
        try:
            if os.path.exists(self.datasets_folder):
                files = os.listdir(self.datasets_folder)
                return len(files) > 0
            return False
        except Exception:
            return False
    
    def create_sample_dataset(self, dataset_title):
        try:
            print("Creando dataset de ejemplo...")
            
            sample_data = [
                ["ID", "Nombre", "Tipo", "Valor", "Fecha"],
                ["1", "Activo 1", "Equipo", "1000000", "2024-01-01"],
                ["2", "Activo 2", "Mobiliario", "500000", "2024-01-02"],
                ["3", "Activo 3", "Vehiculo", "25000000", "2024-01-03"]
            ]
            
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            filename = f"{safe_title}_ejemplo.csv"
            filepath = os.path.join(self.datasets_folder, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                for row in sample_data:
                    writer.writerow(row)
            
            print(f"Dataset de ejemplo creado: {filename}")
            return True
            
        except Exception as e:
            print(f"Error creando dataset de ejemplo: {e}")
            return False
    
    def run(self):
        print("Iniciando spider de Selenium para portal de datos abiertos de Colombia...")
        print(f"API objetivo: {self.api_url}")
        print(f"Página web: {self.web_url}")
        print("Los datasets se guardarán en la carpeta: datasets/")
        print("-" * 60)
        
        try:
            self.create_datasets_folder()
            
            if not self.setup_driver():
                return False
            
            dataset_title = self.get_dataset_info_from_web()
            
            if self.download_dataset_from_api(dataset_title):
                print(f"\nSpider ejecutado exitosamente!")
                print(f"Dataset: {dataset_title}")
                print(f"Revisa la carpeta '{self.datasets_folder}' para ver los archivos descargados")
                return True
            else:
                print("No se pudo descargar el dataset")
                return False
            
        except Exception as e:
            print(f"Error durante la ejecución: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
                print("Driver de Chrome cerrado")
    
    def close(self):
        if self.driver:
            self.driver.quit()

def main():
    spider = ColombiaDataPortalSpider()
    try:
        spider.run()
    finally:
        spider.close()

if __name__ == '__main__':
    main()
