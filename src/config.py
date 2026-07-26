import os

# DIRECTORIOS BASE
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_DIR = os.path.join(BASE_DIR, 'db')
PROMPT_DIR = os.path.join(BASE_DIR, 'prompts')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
APP_DIR = os.path.join(BASE_DIR, 'app')
ENR_DIR = os.path.join(BASE_DIR, 'resources')


#NAMES------------------------------------------------------------------------
page_title = "Chatbot RK Iglesias"
table_name = "inmuebles"
db_search_callback = "Buscando tu piso ideal..."

#ENDPOINTS--------------------------------------------------------------------

#------database------
VECTOR_DB_dir= os.path.join(DB_DIR, 'index.faiss')
sql_search_dir= os.path.join(DB_DIR, 'inmuebles.db')
json_view_data_dir= os.path.join(DB_DIR, 'json_view_data.json')

#------data------
EXCEL_dir = os.path.join(DATA_DIR, 'excel')
CSV_dir = os.path.join(DATA_DIR, 'csv')
PDF_dir = os.path.join(DATA_DIR, 'pdf')
JSON_dir = os.path.join(DATA_DIR, 'json')
TEXT_dir = os.path.join(DATA_DIR, 'text')

COLUMNS_DESCRIPTION_dir = os.path.join(CSV_dir, 'inmuebles/COLUMNS_DESCRIPTION.txt')
TABLE_DESCRIPTION_inm_dir = os.path.join(CSV_dir, 'inmuebles/TABLE_DESCRIPTION.txt')
raw_total_inm_csv_dir = os.path.join(CSV_dir, 'raw_total_inm.csv')
clean_total_inm_csv_dir = os.path.join(CSV_dir, 'clean_total_inm.csv')
raw_total_inm_json_dir = os.path.join(JSON_dir, 'raw_total_inm.json')
columns_dir = os.path.join(JSON_dir, 'columns.json')
localizations_dir = os.path.join(JSON_dir, 'localizations.json')
reverse_geocode_inm_csv_dir = os.path.join(CSV_dir, 'reverse_geocode_inm.csv')

#------DATA GENERATION------
DATA_GEN_DIR = os.path.join(APP_DIR, 'data_generation')

#------ENRICHMENTS------
contact_info_json_dir = os.path.join(ENR_DIR, 'contact_info.json')
tool_instructions_dir = os.path.join(ENR_DIR, 'tool_instructions.json')
search_table_generation_query_dir = os.path.join(ENR_DIR, 'search_table_generation_query.txt')
welcome_dir = os.path.join(ENR_DIR, 'welcome.txt')

#------PROMPTS------
PRESENTATION_PROMPT_dir = os.path.join(PROMPT_DIR, 'PRESENTATION_PROMPT.txt')
CLASSIFICATION_PROMPT_dir = os.path.join(PROMPT_DIR, 'CLASSIFICATION_PROMPT.txt')
CONFIRM_FORM_PROMPT_dir = os.path.join(PROMPT_DIR, 'CONFIRM_FORM_PROMPT.txt')
CONTACT_PROMPT_dir = os.path.join(PROMPT_DIR, 'CONTACT_PROMPT.txt')
OFF_TOPIC_PROMPT_dir = os.path.join(PROMPT_DIR, 'OFF_TOPIC_PROMPT.txt')
ANSWER_NAME_PROMPT_dir = os.path.join(PROMPT_DIR, 'ANSWER_NAME_PROMPT.txt')
NAME_PROMPT_dir = os.path.join(PROMPT_DIR, 'NAME_PROMPT.txt')

RAG_PROMPTS = os.path.join(PROMPT_DIR, 'rag_chain')
RAG_CHAIN_PROMPT_dir = os.path.join(RAG_PROMPTS, 'RAG_CHAIN_PROMPT.txt')

QA_PROMPTS = os.path.join(PROMPT_DIR, 'qa_chain')
QA_GENERAL_PROMPT_dir = os.path.join(QA_PROMPTS, 'QA_GENERAL_PROMPT.txt')
CHECK_QUERY_PROMPT_dir = os.path.join(QA_PROMPTS, 'CHECK_QUERY_PROMPT.txt')
GENERATE_SQL_QUERY_PROMPT_dir = os.path.join(QA_PROMPTS, 'GENERATE_SQL_QUERY_PROMPT.txt')
GENERIC_ANSWER_PROMPT_dir = os.path.join(QA_PROMPTS, 'GENERIC_ANSWER_PROMPT.txt')
BROAD_QUERY_PROMPT_dir = os.path.join(QA_PROMPTS, 'BROAD_QUERY_PROMPT.txt')
SPECIFIC_ANSWER_PROMPT_dir = os.path.join(QA_PROMPTS, 'SPECIFIC_ANSWER_PROMPT.txt')
QA_TOOL_EXPLANATION_dir = os.path.join(QA_PROMPTS, 'QA_TOOL_EXPLANATION.txt')
MORE_INFO_PROMPT_dir = os.path.join(QA_PROMPTS, 'MORE_INFO_PROMPT.txt')
FINANCIAL_INFO_PROMPT_dir = os.path.join(QA_PROMPTS, 'FINANCIAL_INFO_PROMPT.txt')
FINANCIAL_PARSER_PROMPT_dir = os.path.join(QA_PROMPTS, 'FINANCIAL_PARSER_PROMPT.txt')

VISIT_PROMPTS = os.path.join(PROMPT_DIR, 'visit_chain')
ID_OF_INTEREST_PROMPT_dir = os.path.join(VISIT_PROMPTS, 'ID_OF_INTEREST.txt')
CONFIRM_VISIT_PROMPT_dir = os.path.join(VISIT_PROMPTS, 'CONFIRM_VISIT_PROMPT.txt')