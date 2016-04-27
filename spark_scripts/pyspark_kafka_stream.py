__author__ = 'tyler'
from interface import predictTweet
import json
import sys
import pyspark_cassandra
import pyspark_cassandra.streaming
from pyspark.streaming import StreamingContext
from pyspark.streaming.kafka import KafkaUtils


def db_dict(d, sent):
    d.update({'sentiment':sent,'user':d['uid']})
    return d


def clean_str(str):
    import re
    str=str+" "
    str=re.sub("http[^ ]*[\\\]","\\\\",str)                    #Remove hyperlinks
    str=re.sub("http[^ ]* "," ",str)                           #Remove hyperlinks
    str=str.replace('\\n',' ')
    arr=re.findall(r"\w+(?:[-']\w+)*|'|[:)-.(]+|\S\w*", str)   #Single punctuation mark is removed, smileys remain intact
    arr=[i for i in arr if len(i)>1 and i[0]!='@']             #Remove words starting with @ (Twitter mentions)
    arr=[i if i[0]!='#' else i[1:] for i in arr]               #Remove '#' from hashtags
    #arr=[i for i in arr if i!='http' and i!='com' and i!='org']
    res=" ".join(arr)
    return res.lower().strip()


if __name__ == 'main':

brokers, topic = sys.argv[1:]

sc = pyspark_cassandra.CassandraSparkContext()
ssc = StreamingContext(sc, 1)

kvs = KafkaUtils.createDirectStream(ssc,
                                    [topic],
                                    {"metadata.broker.list": brokers})

clean_text = kvs.map(lambda x: json.loads(x[1])) \
                .map(lambda x: (x, clean_str(x['text'])))

db_dict = clean_text.map(lambda x: db_dict(x[0], predictTweet(x[1])['pos']))

trump = db_dict.filter(lambda x: x['candidate'] == 'trump')
hillary = db_dict.filter(lambda x: x['candidate'] == 'hillary')
bernie = db_dict.filter(lambda x: x['candidate'] == 'bernie')
zodiac_killer = db_dict.filter(lambda x: x['candidate'] == 'cruz')
parties = db_dict.filter(lambda x: x['candidate'] == 'parties')

if not trump.isEmpty():
    ssc.saveToCassandra('db', 'trump')
if not hillary.isEmpty():
    ssc.saveToCassandra('db', 'hillary')
if not bernie.isEmpty():
    ssc.saveToCassandra('db', 'bernie')
if not zodiac_killer.isEmpty():
    ssc.saveToCassandra('db', 'cruz')
if not parties.isEmpty():
    ssc.saveToCassandra('db', 'parties')
    
ssc.start()
ssc.awaitTermination()