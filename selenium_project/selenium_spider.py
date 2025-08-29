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
        self.wait = None
        
    def setup_driver(self):
        try:
            chrome_options = webdriver.ChromeOptions()
            # chrome_options.add_argument("--headless")  # Commented out for debugging
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Setup WebDriverWait
            self.wait = WebDriverWait(self.driver, 15)
            
            return True
            
        except Exception as e:
            print(f"Error al configurar el driver: {e}")
            return False
    
    def create_datasets_folder(self):
        if not os.path.exists(self.datasets_folder):
            os.makedirs(self.datasets_folder)
            print(f"Carpeta '{self.datasets_folder}' creada")
        else:
            # Clean old files
            for file in os.listdir(self.datasets_folder):
                if file.endswith('_ejemplo.csv'):
                    os.remove(os.path.join(self.datasets_folder, file))
                    print(f"Archivo de ejemplo removido: {file}")
    
    def get_dataset_info_from_web(self):
        try:
            print(f"Navegando a la página web: {self.web_url}")
            self.driver.get(self.web_url)
            
            # Wait for page to load completely
            time.sleep(10)
            
            try:
                # Try multiple selectors for the title
                title_selectors = [
                    'h1',
                    'h2', 
                    '.dataset-title',
                    '.page-title',
                    '[data-testid="title"]',
                    '.title'
                ]
                
                title = None
                for selector in title_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.text.strip():
                            title = element.text.strip()
                            break
                    except:
                        continue
                
                if not title:
                    # Try to get title from URL or page metadata
                    title = self.driver.title
                    if not title or title == "Datos.gov.co":
                        title = "Activos-de-Informacion-Alcaldia-de-Mistrat"
                
                print(f"Dataset encontrado: {title}")
                return title
                
            except Exception as e:
                print(f"Error obteniendo título: {e}")
                return "Activos-de-Informacion-Alcaldia-de-Mistrat"
            
        except Exception as e:
            print(f"Error obteniendo información de la web: {e}")
            return "Activos-de-Informacion-Alcaldia-de-Mistrat"
    
    def download_dataset_from_api(self, dataset_title):
        try:
            print(f"Intentando descargar dataset desde la API: {self.api_url}")
            
            # Enhanced headers to avoid 403
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.datos.gov.co/',
                'Origin': 'https://www.datos.gov.co'
            }
            
            # First try with GET request
            response = requests.get(self.api_url, headers=headers, timeout=30)
            
            if response.status_code == 403:
                print("Acceso denegado con GET. Intentando con POST...")
                # Try POST request with different approach
                post_data = {
                    "query": "SELECT * LIMIT 1000"
                }
                response = requests.post(self.api_url, headers=headers, json=post_data, timeout=30)
            
            if response.status_code == 403:
                print("Acceso denegado también con POST. Intentando método alternativo...")
                return self.download_dataset_from_web(dataset_title)
            
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                print("Respuesta no es JSON válido. Intentando método alternativo...")
                return self.download_dataset_from_web(dataset_title)
            
            if 'data' not in data or not data['data']:
                print("No se encontraron datos en la respuesta de la API")
                return self.download_dataset_from_web(dataset_title)
            
            dataset_data = data['data']
            print(f"Datos obtenidos de la API: {len(dataset_data)} registros")
            
            # Get column names
            if 'meta' in data and 'view' in data['meta'] and 'columns' in data['meta']['view']:
                columns = [col['name'] for col in data['meta']['view']['columns']]
            else:
                # Try to infer columns from first row
                if dataset_data and len(dataset_data) > 0:
                    columns = [f"Columna_{i}" for i in range(len(dataset_data[0]))]
                else:
                    print("No se pueden determinar las columnas")
                    return self.download_dataset_from_web(dataset_title)
            
            # Save as CSV
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            csv_filename = f"{safe_title}_API.csv"
            csv_filepath = os.path.join(self.datasets_folder, csv_filename)
            
            with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                for row in dataset_data:
                    writer.writerow(row)
            
            print(f"Dataset guardado como CSV desde API: {csv_filename}")
            
            # Save as JSON
            json_filename = f"{safe_title}_API.json"
            json_filepath = os.path.join(self.datasets_folder, json_filename)
            
            with open(json_filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Dataset guardado como JSON desde API: {json_filename}")
            
            return True
            
        except Exception as e:
            print(f"Error descargando desde la API: {e}")
            print("Intentando descarga desde la página web...")
            return self.download_dataset_from_web(dataset_title)
    
    def download_dataset_from_web(self, dataset_title):
        try:
            print("Intentando descargar dataset desde la página web...")
            
            # Wait for page to be fully loaded
            time.sleep(5)
            
            # First, let's try to find the data table or view
            print("Buscando tabla de datos o vista de datos...")
            
            # Look for data table elements
            table_selectors = [
                'table',
                '.data-table',
                '.dataset-table',
                '[data-testid="data-table"]',
                '.table-responsive table',
                '.data-view table'
            ]
            
            data_table = None
            for selector in table_selectors:
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if table:
                        data_table = table
                        print(f"Tabla de datos encontrada con selector: {selector}")
                        break
                except:
                    continue
            
            if data_table:
                print("Extrayendo datos de la tabla...")
                return self.extract_data_from_table(data_table, dataset_title)
            
            # If no table found, look for download links
            print("No se encontró tabla de datos. Buscando enlaces de descarga...")
            
            # Look for download links with multiple strategies
            download_selectors = [
                'a[href*=".csv"]',
                'a[href*=".xlsx"]', 
                'a[href*=".xls"]',
                'a[href*="download"]',
                'a[href*="export"]',
                'button[class*="download"]',
                'a[class*="download"]',
                'a[title*="descargar"]',
                'a[title*="download"]',
                'a[aria-label*="descargar"]',
                'a[aria-label*="download"]'
            ]
            
            download_elements = []
            for selector in download_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    download_elements.extend(elements)
                except:
                    continue
            
            # Remove duplicates
            download_elements = list(set(download_elements))
            
            if not download_elements:
                print("No se encontraron enlaces de descarga. Buscando en toda la página...")
                # Search for any links that might contain file extensions
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if href and any(ext in href.lower() for ext in ['.csv', '.xlsx', '.xls', 'download', 'export']):
                            download_elements.append(link)
                    except:
                        continue
            
            if not download_elements:
                print("No se encontraron elementos de descarga en la página web")
                return False
            
            print(f"Encontrados {len(download_elements)} elementos de descarga")
            
            # Try each download element
            for i, element in enumerate(download_elements):
                try:
                    print(f"Intentando descarga {i+1}/{len(download_elements)}")
                    
                    if element.tag_name == 'a':
                        href = element.get_attribute('href')
                        if href:
                            if href.startswith('http'):
                                print(f"Enlace directo encontrado: {href}")
                                if self.download_file_from_url(href, dataset_title, i):
                                    return True
                            else:
                                # Relative URL, make it absolute
                                absolute_url = urljoin(self.web_url, href)
                                print(f"Enlace relativo convertido: {absolute_url}")
                                if self.download_file_from_url(absolute_url, dataset_title, i):
                                    return True
                    
                    elif element.tag_name == 'button':
                        print("Haciendo clic en botón de descarga...")
                        try:
                            element.click()
                            time.sleep(5)
                            
                            # Check if download started
                            if self.check_download_folder():
                                print("Descarga exitosa mediante clic en botón")
                                return True
                        except Exception as click_error:
                            print(f"Error al hacer clic: {click_error}")
                            continue
                
                except Exception as e:
                    print(f"Error con elemento {i+1}: {e}")
                    continue
            
            print("No se pudo descargar desde ningún elemento")
            return False
            
        except Exception as e:
            print(f"Error en descarga desde web: {e}")
            return False
    
    def extract_data_from_table(self, table, dataset_title):
        """Extract data from HTML table and save as CSV"""
        try:
            print("Extrayendo datos de la tabla HTML...")
            
            # Get headers
            headers = []
            try:
                header_row = table.find_element(By.TAG_NAME, "thead").find_elements(By.TAG_NAME, "th")
                headers = [th.text.strip() for th in header_row if th.text.strip()]
            except:
                # Try to get headers from first row
                try:
                    first_row = table.find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")[0]
                    headers = [td.text.strip() for td in first_row.find_elements(By.TAG_NAME, "td") if td.text.strip()]
                except:
                    headers = []
            
            if not headers:
                # Generate generic headers
                first_row = table.find_elements(By.TAG_NAME, "tr")[0]
                headers = [f"Columna_{i+1}" for i in range(len(first_row.find_elements(By.TAG_NAME, "td")))]
            
            # Get data rows
            rows = []
            try:
                tbody = table.find_element(By.TAG_NAME, "tbody")
                data_rows = tbody.find_elements(By.TAG_NAME, "tr")
            except:
                # If no tbody, get all rows
                data_rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in data_rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        row_data = [cell.text.strip() for cell in cells]
                        rows.append(row_data)
                except:
                    continue
            
            if not rows:
                print("No se encontraron filas de datos en la tabla")
                return False
            
            print(f"Extraídos {len(rows)} filas de datos de la tabla")
            
            # Save as CSV
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            
            csv_filename = f"{safe_title}_tabla.csv"
            csv_filepath = os.path.join(self.datasets_folder, csv_filename)
            
            with open(csv_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(row)
            
            print(f"Dataset extraído de tabla y guardado como CSV: {csv_filename}")
            return True
            
        except Exception as e:
            print(f"Error extrayendo datos de la tabla: {e}")
            return False
    
    def download_file_from_url(self, url, dataset_title, index):
        try:
            print(f"Descargando archivo desde: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': self.web_url
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Determine file extension from URL or content type
            content_type = response.headers.get('content-type', '').lower()
            
            if '.csv' in url.lower() or 'csv' in content_type:
                extension = '.csv'
            elif '.xlsx' in url.lower() or 'excel' in content_type or 'spreadsheet' in content_type:
                extension = '.xlsx'
            elif '.xls' in url.lower():
                extension = '.xls'
            else:
                # Try to determine from content
                if 'csv' in content_type or 'text/plain' in content_type:
                    extension = '.csv'
                elif 'excel' in content_type or 'spreadsheet' in content_type:
                    extension = '.xlsx'
                else:
                    extension = '.csv'  # Default to CSV
            
            safe_title = re.sub(r'[^\w\s-]', '', dataset_title).strip()
            safe_title = re.sub(r'[-\s]+', '-', safe_title)
            filename = f"{safe_title}_web_{index+1}{extension}"
            filepath = os.path.join(self.datasets_folder, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Archivo descargado exitosamente: {filename}")
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
    
    def run(self):
        print("Iniciando spider de Selenium para portal de datos abiertos de Colombia...")
        print(f"API objetivo: {self.api_url}")
        print(f"Página web: {self.web_url}")
        print("Los datasets se guardarán en la carpeta: datasets/")
        print("-" * 60)
        
        try:
            self.create_datasets_folder()
            
            if not self.setup_driver():
                print("Error: No se pudo configurar el driver de Chrome")
                return False
            
            dataset_title = self.get_dataset_info_from_web()
            
            # Try API first, then web as fallback
            if self.download_dataset_from_api(dataset_title):
                print(f"\n✅ Spider ejecutado exitosamente desde la API!")
                print(f"Dataset: {dataset_title}")
                print(f"Revisa la carpeta '{self.datasets_folder}' para ver los archivos descargados")
                return True
            else:
                print("❌ No se pudo descargar el dataset desde ningún método")
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
        success = spider.run()
        if success:
            print("\n🎉 Proceso completado exitosamente!")
        else:
            print("\n❌ El proceso no se pudo completar")
            print("Revisa los mensajes de error anteriores para más detalles")
    finally:
        spider.close()

if __name__ == '__main__':
    main()
