import os
from dotenv import load_dotenv

base_dir = os.path.join(os.path.dirname(__file__), '../').replace("\\", "/").replace("src/../", "")
load_dotenv(f'{base_dir}.env')

ignored_folders = [f'{base_dir}data/sportsipy/', f'{base_dir}data/natural_stat_trick/']
for fdr in ignored_folders:
    if not os.path.exists(fdr):
        os.makedirs(fdr)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0'

# for transformers
device = "cuda"
