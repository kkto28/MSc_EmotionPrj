1)Following packages are need:
a) Tweepy https://www.tweepy.org/ 
b) Pymongo https://api.mongodb.com/python/current/ 
c) Natural Language Toolkit https://www.nltk.org 
d) Stop-words https://pypi.org/project/stop-words/ 
e) Data-pack https://pypi.org/project/datapackage/ 
f) Emoji https://pypi.org/project/emoji/ 
g) Demoji https://pypi.org/project/demoji/ 

2)Following configuration can be changed for connecting MongoDB 
DB_CONNECTION="mongodb://localhost:27017/"
DB_NAME="EmotionPrj"
DB_COL="EmotionCol"

3)Program run under python terminal
python.exe "twittercrawler.py"

4)twittercrawler.py 
contains three classes and main for execution
-TwitterCrawler, tweets crawling, filtering, processing, and storing
-TextCleanProcessor, cleaning data e.g. removing stopwords, repeat words, punctuation, tokenization

5)Project is present as following hierarchy
Root Folder
-twittercrawler.py, main program for crawling, data process and storing
Datasample_20200221 Folder
-20_sample_data sub folder, 20 data samples per class used in crowd sourcing
-mongodb sub folder, full data exported from MongoDb in csv format
Log Folder
-result_20200221_log.txt, dump out log during execution
CF_reports Folder, reports downloaded from crowd sourcing site



