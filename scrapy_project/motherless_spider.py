import scrapy
import csv
import re
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

class MotherlessHomesSpider(scrapy.Spider):
    name = 'motherless_homes'
    start_urls = ['https://worldmetrics.org/motherless-homes-statistics/']
    
    def parse(self, response):
        key_findings = response.css('ul.space-y-4 li p.text-base.sm\\:text-lg.text-gray-800.leading-relaxed::text').getall()
        slideshow_stats = response.css('div:contains("Statistic") p::text').getall()
        section_titles = response.css('h2, h3::text').getall()
        content_paragraphs = response.css('p::text').getall()
        
        csv_data = []
        
        for i, finding in enumerate(key_findings, 1):
            if finding.strip():
                csv_data.append({
                    'category': 'Key Findings',
                    'statistic_number': i,
                    'description': finding.strip(),
                    'value': self.extract_value(finding),
                    'unit': self.extract_unit(finding)
                })
        
        for i, stat in enumerate(slideshow_stats, 1):
            if stat.strip() and len(stat.strip()) > 10:
                csv_data.append({
                    'category': 'Slideshow Statistics',
                    'statistic_number': i,
                    'description': stat.strip(),
                    'value': self.extract_value(stat),
                    'unit': self.extract_unit(stat)
                })
        
        for section_title in section_titles:
            if section_title.strip():
                try:
                    section_content = response.css('p::text').getall()
                    for content in section_content:
                        if content.strip() and section_title.strip().lower() in content.lower():
                            if len(content.strip()) > 10:
                                csv_data.append({
                                    'category': section_title.strip(),
                                    'statistic_number': len([x for x in csv_data if x['category'] == section_title.strip()]) + 1,
                                    'description': content.strip(),
                                    'value': self.extract_value(content),
                                    'unit': self.extract_unit(content)
                                })
                except Exception as e:
                    self.logger.warning(f"Error procesando sección {section_title}: {e}")
                    continue
        
        for i, paragraph in enumerate(content_paragraphs, 1):
            if paragraph.strip() and len(paragraph.strip()) > 20:
                if re.search(r'\d+%|\$\d+|\d+(?:,\d+)?\s*(?:homes?|puppies?|kittens?|animals?|pets?)', paragraph):
                    csv_data.append({
                        'category': 'Content Statistics',
                        'statistic_number': i,
                        'description': paragraph.strip(),
                        'value': self.extract_value(paragraph),
                        'unit': self.extract_unit(paragraph)
                    })
        
        self.save_to_csv(csv_data, 'motherless_homes_statistics.csv')
        
        for item in csv_data:
            yield item
    
    def extract_value(self, text):
        percentage_match = re.search(r'(\d+(?:\.\d+)?)\s*%', text)
        if percentage_match:
            return percentage_match.group(1)
        
        dollar_match = re.search(r'\$(\d+(?:,\d+)?)', text)
        if dollar_match:
            return dollar_match.group(1).replace(',', '')
        
        number_match = re.search(r'(\d+(?:,\d+)?)', text)
        if number_match:
            return number_match.group(1).replace(',', '')
        
        return "N/A"
    
    def extract_unit(self, text):
        if '%' in text:
            return 'percentage'
        elif '$' in text:
            return 'dollars'
        elif 'months' in text or 'years' in text or 'days' in text:
            return 'time'
        elif any(word in text.lower() for word in ['homes', 'puppies', 'kittens', 'animals', 'pets']):
            return 'count'
        else:
            return 'ratio'
    
    def save_to_csv(self, data, filename):
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['category', 'statistic_number', 'description', 'value', 'unit']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        self.logger.info(f'Datos guardados en {filename}')

def run_spider():
    process = CrawlerProcess(get_project_settings())
    process.crawl(MotherlessHomesSpider)
    process.start()

if __name__ == '__main__':
    run_spider()
