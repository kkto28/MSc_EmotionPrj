import pymongo
import tweepy
import json
import ssl
import time
import re
import emoji
import demoji
from datetime import datetime
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from string import punctuation 
from nltk.corpus import stopwords
from requests.exceptions import Timeout, ConnectionError
from requests.packages.urllib3.exceptions import ReadTimeoutError


# ***need download nltk punkt, stopwords datapack

# Twitter API credentials
TW_API_KEY="ZuLyJmWyaoiq9zrM4TtuD1ad5"
TW_API_SECRET="2d26bPDXLau1Z898buP0woMzWR6v91SLqEJocv6xZuWll1CmXt"
TW_ACCESS_TOKEN="102319768-GxFkI3heA62uLSCyvZDXX00F0b7P0aCZ9vwzhrLs"
TW_ACCESS_TOKEN_SECRET="hx0lwXm8v1j7VtNlXkPQ6mt54ORJDKJ90wlVaKehR1IER"
# Mongo DB url, DB name and collection name
DB_CONNECTION="mongodb://localhost:27017/"
DB_NAME="EmotionPrj"
DB_COL="EmotionCol"
# Parameters that are configurable
NUM_TWEETS_PER_PAGE= 50 # Pagination, no. of tweets per page
NUM_TWEET_MORE_TIMES=3 # Get more Tweets for selecting those with better quality
TEXT_LEN= 80 # Min length of tweet

# Hashtag used for emotional groups
emotion_classify_hashtag = {
    "excitement":"excite,excitement",
    "happy":"happy,joy",
    "pleasant":"pleasant",
    "surprise":"surprise,sad,frustration",
    "fear":"fear,depression,disgust",
    "angry":"angry"
}
#Plus emoji used for emotional groups
emotion_classify_emoji = {
    "excitement":":rolling_on_the_floor_laughing: OR :face_with_tears_of_joy:",
    "happy":":grinning_face: OR :grinning_face_with_big_eyes: OR :grinning_face_with_smiling_eyes: OR :face_blowing_a_kiss:",
    "pleasant":":slightly_smiling_face: OR :upside-down_face:",
    "surprise":":face_with_open_mouth:",
    "fear":":fearful_face: OR :anxious_face_with_sweat: OR :face_screaming_in_fear:",
    "angry":":face_with_steam_from_nose: OR :pouting_face: OR :angry_face: OR :face_with_symbols_on_mouth: OR :angry_face_with_horns:"
}

#Crawler to get tweets by using tweepy
class TwitterCrawler():

    def __init__(self):
        # Perform Twitter authentication
        auth = tweepy.OAuthHandler(TW_API_KEY, TW_API_SECRET)
        auth.set_access_token(TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
        # Create api object
        self.twapi = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        
        # Searching parameters
        # Number of tweets per page
        self.no_tweets_per_page= NUM_TWEETS_PER_PAGE
        # Filter by language
        self.lang = "en"
        # Filter by recent, popular or mixed.
        self.result_type = "recent"
        # Tweet mode as extended to return full text in text
        self.tweet_mode="extended"
        # Include entities
        self.include_entities = True
        # Contains raw tweets
        self.tweets = []
        # Contains tweets that were cleaned
        self.processed_tweets = []
        # Contains tweeter id
        self.tweet_id_lst = []

    # Function for handling pagination in our search
    @staticmethod
    def limit_handled(cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.RateLimitError:
                print('Expetion limit_handled: sleep 15 minutes')
                time.sleep(15 * 60)
            except StopIteration:
                print('end crawling***')
                break
    # Function for checking hashtag with overlapping class or not
    def check_tag_overlap(self,classify,input):
        overlaplst= []
        #print(".")
        for k in emotion_classify_hashtag:
            if k != classify:
                cktags= emotion_classify_hashtag[k].split(",")
                for t in cktags:
                    if t in str.lower(str(input)):
                        overlaplst.append(t)
        return overlaplst

    # Function for make the search using Twitter API
    def crawl_tweets(self, search_key, total_tweets):

        try:
            outstandings= total_tweets
            no_tweets_searched= 0
            no_fetch= total_tweets*NUM_TWEET_MORE_TIMES
            self.tweets.clear()
            sk1 = 0
            sk2 = 0
            sk3 = 0
            print("processing....pls. wait")
            while outstandings > 0:
                # performs the search
                for tweet in self.limit_handled(tweepy.Cursor(self.twapi.search,
                                        q=search_key,
                                        count=self.no_tweets_per_page,
                                        tweet_mode=self.tweet_mode,
                                        lang=self.lang,
                                        result_type=self.result_type,
                                        include_entities=self.include_entities).items(no_fetch)):

                    if not tweet.id in self.tweet_id_lst:
                        if len(tweet.full_text) > TEXT_LEN:
                            overlap= self.check_tag_overlap("happy",tweet._json["entities"]["hashtags"])
                            if len(overlap)==0:
                                #print(str(no_tweets_searched))
                                #print(demoji.findall(str(tweet.full_text)))
                                #print(tweet.full_text)
                                self.tweets.append(tweet._json)
                                self.tweet_id_lst.append(tweet.id)

                                no_tweets_searched+=1
                                if len(self.tweets) == total_tweets:
                                    print("finished fetching...")
                                    break
                            else:
                                #print("skip overlapping")
                                sk1+=1
                        else:
                            #print("skip short text")
                            sk2+=1
                    else:
                        #print("skip replicated")
                        sk3+=1

                outstandings= outstandings - no_tweets_searched
                if outstandings > NUM_TWEETS_PER_PAGE:
                    no_fetch = outstandings
                else:
                    no_fetch = NUM_TWEETS_PER_PAGE

                no_tweets_searched = 0
                #print("outstanding tweets ...", outstandings )

            print( "skip overlap " + str(sk1))
            print( "skip short text " + str(sk2))
            print( "skip replicated " + str(sk3))
        except  Exception as e:
            print('Exception from crawl_tweets:', e)
            pass

    # Processing....
    def store_tweets(self):
        client = pymongo.MongoClient(DB_CONNECTION)
        db = client[DB_NAME]
        col = db[DB_COL]
        x = col.insert_many(self.processed_tweets)
        #print list of the _id values of the inserted documents:
        print('Tweets saved to db.... \n')
        #print(x.inserted_ids)

    def process_tweets(self, classify):
        cleaner = TextCleanProcessor()
        for tweet in self.tweets:
            tweetId = tweet['id_str'] #tweet id
            timeTweet = tweet['created_at'] #tweet date time
            content = cleaner.process(tweet['full_text']) #cleaned tweet
            tweetUrl = "https://twitter.com/"+ tweet['user']['screen_name'] + "/statuses/" + tweetId #tweet url
            jobj = {"classify": classify, "tweetId": tweetId , "timeTweet": timeTweet, "tweetUrl":tweetUrl, "text_cleaned": ' '.join(content), "text_origin":re.sub('\n',' ',re.sub(',',' ', tweet['full_text'])) }
            self.processed_tweets.append(jobj) #push to buffer
            #print(tweetId + " " + timeTweet + " " + ' '.join(content) + " " + tweetUrl + "\n")
        print("total emoji count " + str(cleaner.emoji_counter))


class TextCleanProcessor:

    def __init__(self):
        self.replacement_patterns = [
        (r'won\'t', 'will not'),
        (r'can\'t', 'cannot'),
        (r'i\'m', 'i am'),
        (r'ain\'t', 'is not'),
        (r'(\w+)\'ll', '\g<1> will'),
        (r'(\w+)n\'t', '\g<1> not'),
        (r'(\w+)\'ve', '\g<1> have'),
        (r'(\w+)\'s', '\g<1> is'),
        (r'(\w+)\'re', '\g<1> are'),
        (r'(\w+)\'d', '\g<1> would'),
        (r'won\’t', 'will not'),
        (r'can\’t', 'cannot'),
        (r'i\’m', 'i am'),
        (r'ain\’t', 'is not'),
        (r'(\w+)\’ll', '\g<1> will'),
        (r'(\w+)n\’t', '\g<1> not'),
        (r'(\w+)\’ve', '\g<1> have'),
        (r'(\w+)\’s', '\g<1> is'),
        (r'(\w+)\’re', '\g<1> are'),
        (r'(\w+)\’d', '\g<1> would')
        ]
        self._stopwords = set(stopwords.words('english') + list(punctuation) + ['AT_USER','URL'])
        self.repeat_regexp= re.compile(r'(\w*)(\w)\2(\w*)')
        self.patterns = [(re.compile(regex),repl) for (regex, repl) in self.replacement_patterns]
        #print(self.patterns)
        self.repl = r'\1\2\3'
        self.emoji_counter = 0

    # Function to replace abbev.
    def replace(self, text):
        s= text
        for(pattern, repl) in self.patterns:
            s= re.sub(pattern, repl, s)
        return s

    # Function to replace repeat words e.g. Looooove to Love
    def replace_repeatwords(self, word):
        if wordnet.synsets(word):
            return word
        repl_word = self.repeat_regexp.sub(self.repl, word)
        if repl_word != word:
            return self.replace_repeatwords(repl_word)
        else:
            return repl_word

    def process(self, tweet_text):
        num_emoji = emoji.emoji_count(tweet_text)
        self.emoji_counter+=num_emoji
        #print(num_emoji)
        tweet_text = tweet_text.lower() # convert text to lower-case
        tweet_text = re.sub('((www\.[^\s]+)|(https?://[^\s]+))', 'URL', tweet_text) # remove URLs
        tweet_text = re.sub('@[^\s]+', 'AT_USER', tweet_text) # remove usernames
        tweet_text = re.sub(r'#([^\s]+)', r'\1', tweet_text) # remove the # in #hashtag
        tweet_text = emoji.demojize(tweet_text) # repace emoji icon by word
        tweet_text = re.sub(':', ' ', tweet_text) # :emoji word
        tweet_text = word_tokenize(self.replace(tweet_text)) # replace abbrev. and perform tokenization
        # remove repeated characters (helloooooooo into hello) and stopwords
        return [self.replace_repeatwords(word) for word in tweet_text if word not in self._stopwords]        

# Function to create search key for tweeter api filtering
def create_search_key(classify):
    searching_hash= ""
    cktags= emotion_classify_hashtag[classify].split(",")
    for t in cktags:
        searching_hash += t + " OR "
    searching_hash += emotion_classify_emoji[classify] + " -filter:retweets"
    #searching_hash = searching_hash[:-4] +  " -filter:retweets"
    return searching_hash

if __name__ == "__main__":

    emotion = ("excitement","happy","pleasant","surprise","fear","angry")
    mycrawler = TwitterCrawler()
    now = datetime.now()
    print("start *********" + now.strftime("%m/%d/%Y, %H:%M:%S"))
    #handle emotion crawling and process as per classification
    for e in emotion:
        
        searching_key = create_search_key(e)
        print("-------------"+searching_key)
        t1 = datetime.now()
        mycrawler.crawl_tweets(emoji.emojize(searching_key),150)  #crawl 150 per class
        t2 = datetime.now() 
        
        mycrawler.process_tweets(e) #perform cleaning
        t3 = datetime.now()
        print("data crawl duration s " + str(t2 - t1))
        print("data process duration s " + str(t3 - t2))
        print("total duration s " + str(t3-t1))
        print("-------------")
    t4 = datetime.now()
    
    mycrawler.store_tweets() #store to MongoDB
    end = datetime.now()
    print("storage duration s " + str(end-t4))
    print("end*********" + now.strftime("%m/%d/%Y, %H:%M:%S"))
    print("duration********* s " + str(end - now))