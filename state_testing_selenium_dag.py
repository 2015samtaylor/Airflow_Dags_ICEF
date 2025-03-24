import os
import sys
import logging
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin
from datetime import datetime, timedelta

working_dir = '/home/g2015samtaylor/airflow/git_directory/state_testing/elpac_or_cers'
sys.path.append(working_dir)
# Import your custom modules
from modules.login import *
from modules.file_altering import *
from modules.schools_and_grade import *
from modules.checks import *
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 21),  # Update with your desired start date
    'retries': 1,
    'email_on_failure': True,
    'email_on_retry': True,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
    'email': ['2015samtaylor@gmail.com'],
    'catchup': False,  # Do not backfill the DAG
}

# Define the DAG
with DAG(
    'state_testing_selenium_dag',
    default_args=default_args,
    description='A Dag for State Testing Selenium donwloads',
    schedule_interval='10 4 * * 1-5',  
    catchup=False,
) as dag:
    
    # Define parameters for download directory and destination directory
    download_directory = '/home/g2015samtaylor/airflow/git_directory/state_testing/elpac_or_cers/downloads/'
    destination_dir = '/home/g2015samtaylor/ixl/'
    
    def setup_chrome_driver(download_directory):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = "/home/g2015samtaylor/chrome_selenium_binaries/chrome-linux64/chrome"
        
        os.makedirs(download_directory, exist_ok=True)
        prefs = {'download.default_directory': download_directory,
                 'profile.default_content_setting_values.automatic_downloads': 1,
                 'profile.content_settings.exceptions.automatic_downloads.*.setting': 1}
        chrome_options.add_experimental_option('prefs', prefs)
        
        chrome_driver_path = "/home/g2015samtaylor/chrome_selenium_binaries/chromedriver-linux64/chromedriver"
        service = Service(chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        return driver
    
    # Define a task to run the Selenium script (PythonOperator)
    def run_state_testing_script(download_directory, destination_dir, **kwargs):
        logger = LoggingMixin().log
        logger.info('Starting run_state_testing_script task')
        
        driver = setup_chrome_driver(download_directory)
        clear_directory(download_directory)
        
        def process(driver, default_wait=30):

            login(driver, default_wait=10)
            automation = SchoolGradeAutomation(driver)
            school_name_strings = ['ICEF Vista Middle Academy', 'ICEF Vista Elementary Academy', 
                                'ICEF View Park Preparatory High', 'ICEF View Park Preparatory Middle', 
                                'ICEF View Park Preparatory Elementary', 'ICEF Innovation Los Angeles Charter', 
                                'ICEF Inglewood Elementary Charter Academy']

            for school in school_name_strings:
                automation.download_school_reports(school, '2023-24', test_one='Math Summative', test_two='Summative ELPAC')

            driver.quit()
            target_dir = os.path.join(os.getcwd(), 'stacked_dir')
            stacked = stack_files(download_directory, target_dir)
                    
            logger.info('Selenium Process has concluded')

            destination = os.path.join(destination_dir ,'ixl.csv')
            try:
                stacked.to_csv(destination, index=False)
                print(f'Stacked frame sent to {destination}')
            except Exception as e:
                print(f'Unable to send stacked frame to to {destination} due to {e}')
    
        
        process(driver)
    
    run_selenium_downloads = PythonOperator(
        task_id='run_state_testing_script',
        python_callable=run_state_testing_script,
        op_kwargs={
            'download_directory': download_directory,
            'destination_dir': destination_dir
        },
        dag=dag,
    )

    # Set task dependencies
    run_selenium_downloads
