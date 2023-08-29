from googleapiclient.discovery import build
import streamlit as st
import pymysql
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from datetime import datetime
from PIL import Image


st.set_page_config(
    page_title="YOUTUBE DATA HARVESTING",
    page_icon="https://cdn.pixabay.com/photo/2015/08/11/12/32/youtube-884381_1280.png",
    layout="wide",
    initial_sidebar_state="expanded"
    )
image = Image.open('youtube_data.png')
st.image(image)
st.title (":red[YOUTUBE DATA HARVESTING]") 


api_key='AIzaSyBV6Gu2JzmqfggAUTp9UNC1-Yniu3SRzAU'
# api_key = 'AIzaSyDx4tDViuPLFnILnVzNVb-Q-KL9I-ffYfY'
youtube=build('youtube','v3',developerKey=api_key)

def channel_details(youtube,channel_id):
    
    request = youtube.channels().list(part='snippet,contentDetails,statistics,status', id=channel_id)
    response = request.execute()
    
    data={'channel_id':response['items'][0]['id'],
          'channel_name':response['items'][0]['snippet']['title'],
          'total_video_count':response['items'][0]['statistics']['videoCount'],
          'channel_description':response['items'][0]['snippet']['description'],
          'channel_status':response['items'][0]['status']['privacyStatus'],
          'subscribers':response['items'][0]['statistics']['subscriberCount'],
          'playlist_id':response['items'][0]['contentDetails']['relatedPlaylists']['uploads']}
    return [data]

def get_video_ids(youtube, playlist_id):
    video_ids = []
    next_page_token = None#the beginning ensures that the loop starts with the initial request to get the first page of videos.
    while True:#It will true until get entire video id
        request = youtube.playlistItems().list(part='contentDetails', playlistId=playlist_id, maxResults=50, pageToken=next_page_token)
        response = request.execute()

        for item in response['items']:
            video_ids.append([item['contentDetails']['videoId'],playlist_id])

        next_page_token = response.get('nextPageToken')#retrieves the value of the 'nextPageToken' key from the response dictionary.

        if not next_page_token:
            break

    return video_ids

# Note: The input duration_string is assumed to be in the ISO 8601 duration format, 
#     which consists of P, T, H, M, and S followed by integers representing the duration in years, months,
#     days, hours, minutes, and seconds, respectively.
#     The function, as provided, does not handle durations with years or months; it focuses on hours, minutes, and seconds.

def convert_duration(duration_string):
    # By calling timedelta() without any arguments, the duration
    # object is initialized with a duration of 0 days, 0 seconds, and 0 microseconds. Essentially, it sets the initial duration to zero.
    duration_string = duration_string[2:]  # Remove "PT" prefix
    duration = timedelta()
    
    # Extract hours, minutes, and seconds from the duration string
    if 'H' in duration_string:
        hours, duration_string = duration_string.split('H')
        duration += timedelta(hours=int(hours))
    
    if 'M' in duration_string:
        minutes, duration_string = duration_string.split('M')
        duration += timedelta(minutes=int(minutes))
    
    if 'S' in duration_string:
        seconds, duration_string = duration_string.split('S')
        duration += timedelta(seconds=int(seconds))
    
    # Format duration as H:MM:SS
    duration_formatted = str(duration)
    if '.' in duration_formatted:
        hours, rest = duration_formatted.split(':')
        minutes, seconds = rest.split('.')
        duration_formatted = f'{int(hours)}:{int(minutes):02d}:{int(seconds):02d}'
    else:
        duration_formatted = duration_formatted.rjust(8, '0')
    
    return duration_formatted

def video_data(youtube, video_ids):
    data = []
    
    for video_id in video_ids:
        request = youtube.videos().list(part='snippet,statistics,contentDetails', id=video_id)
        response = request.execute()
        videos = response['items']

        for video in videos:
            title = video['snippet']['title']
            playlist_id = video_id[1]
            
        
            description = video['snippet']['description']
            
            # Convert published timestamp to year-month format
            published_timestamp = video['snippet']['publishedAt']
            published_datetime = datetime.strptime(published_timestamp, '%Y-%m-%dT%H:%M:%SZ')
            published = published_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            view_count = video['statistics'].get('viewCount', 0)
            like_count = int(video['statistics'].get('likeCount', 0))  # Convert like_count to int
            dislike_count = video['statistics'].get('dislikeCount', 0)
            favorite_count = video['statistics'].get('favoriteCount', 0)
            comment_count = video['statistics'].get('commentCount', 0)
            
            # Convert duration string to correct time format
            duration_string = video['contentDetails']['duration']
            duration = convert_duration(duration_string)
            
            thumbnail = video['snippet']['thumbnails']['default']['url']
            caption_status = video['contentDetails']['caption']

            video_data = {
                'video_id': video_id[0],
                'playlist_id': playlist_id,
                'title': title,
                'description': description,
                'published': published,
                'view_count': view_count,
                'like_count': like_count,
                'dislike_count': dislike_count,
                'favorite_count': favorite_count,
                'comment_count': comment_count,
                'duration': duration,
                'thumbnail': thumbnail,
                'caption_status': caption_status
            }

            data.append(video_data)

    return data



def convert_timestamp(timestamp):
    datetime_obj = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    formatted_time = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time

def get_video_comments(youtube, video_ids):
    all_comments = []
    
    for video_id in video_ids:
        try:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id[0],
                textFormat="plainText",
                maxResults=20
            ).execute()
            
            for item in response['items'][:20]:
                comment_info = {
                    'comment_id': item["snippet"]["topLevelComment"]['id'],
                    'video_id': video_id[0],
                    'comment_text': item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                    'comment_author': item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                    'comment_published_at': convert_timestamp(item["snippet"]["topLevelComment"]["snippet"]["publishedAt"])
                }
                
                all_comments.append(comment_info)
                
        except HttpError as e:
            if e.resp.status == 403 and 'commentDisabled' in str(e):
                # Comments are disabled for this video, continue to the next video ID
                pass
            else:
                # An error occurred, continue to the next video ID
                pass
                
    return all_comments

def get_all_data(youtube, channel_id,video_ids):
    all_data = {}

    channel_detail=channel_details(youtube,channel_id)
    all_data['channel_details']=channel_detail

    # Get video data
    video_details =video_data(youtube,video_ids)
    all_data['video_data'] = video_details

#     Get video comments
    video_comments =get_video_comments(youtube,video_ids)
    all_data['video_comments'] = video_comments
    
     # Get playlist ID
# #     playlist_id=playlist_ids
# #     all_data['playlist_ids'] = playlist_id

# #     # Get video IDs from playlist
# #     video_ids = get_video_ids(youtube, playlist_id)
# # #     all_data['video_ids'] = video_ids

    return [all_data]


def insert_to_mongodb(all_data_info):
    import pymongo

    myclient = pymongo.MongoClient("mongodb://localhost:27017")
    mydb = myclient['youtube']
    mycol = mydb["youtube data"]

    mycol.insert_many(all_data_info, ordered=False)

    return True


def create_tables():
    
    import MySQLdb as mysql
    import pandas as pd
    # import mysql.connector
    import pymysql

    # from sqlalchemy import create_engine
    

    
    mydb = pymysql.connect(
        host="localhost",
        user="root",
        # password="Rakul@9360721393",
         password="",
        autocommit=True)
    
    mycursor=mydb.cursor()
    mycursor.execute("CREATE DATABASE if not exists youtubedata")
    mycursor.execute("SHOW DATABASES")
    mycursor.execute("USE youtubedata")
    
    #created table for channeldetails
    channel_info='''CREATE TABLE if not exists channel_data 
                (channel_id VARCHAR(255) PRIMARY KEY,
                channel_name VARCHAR(255),
                total_video_count int,
                channel_description TEXT,
                channel_status VARCHAR(255),
                subscribers int,
                playlist_id VARCHAR(255));'''
    mycursor.execute(channel_info)
    
    #created table for playlist_id
    playlist_info=("CREATE TABLE if not exists playlist_details ("
                 "playlist_id VARCHAR(255) PRIMARY KEY,"
                 "channel_id VARCHAR(255),"
                 "FOREIGN KEY (channel_id) REFERENCES channel_data(channel_id)"
                 ")")
    mycursor.execute(playlist_info)
    
    #created table for video_data
    video_data =  ("CREATE TABLE IF NOT EXISTS Video_data ("
               "video_id VARCHAR(255) NOT NULL PRIMARY KEY,"
               "playlist_id VARCHAR(255),"
               "video_name VARCHAR(255)," 
               "video_description TEXT,"
               "published_date VARCHAR(255),"
               "view_count INT,"
               "like_count INT,"
               "dislike_count INT,"
               "favorite_count INT,"
               "comment_count INT,"
               "duration INT,"
               "thumbnail VARCHAR(255),"
               "caption_status VARCHAR(255),"
               "FOREIGN KEY (playlist_id) REFERENCES playlist_details(playlist_id)"
                   ")")
    mycursor.execute(video_data)
    
    #created table for comment_data
    comment_datas =("CREATE TABLE IF NOT EXISTS Comment_datas ("
                    "comment_id VARCHAR(255) NOT NULL PRIMARY KEY,"
                    "video_id VARCHAR(255),"
                    "comment_text TEXT,"
                    "comment_author VARCHAR(255),"
                    "comment_published_date INT,"
                    "FOREIGN KEY (video_id) REFERENCES video_data(video_id)"
                    ")");
    mycursor.execute(comment_datas)
    

    
def insert_data_to_sql():
        
    import MySQLdb as mysql
    import pandas as pd
    # import mysql.connector
    import pymysql

    # from sqlalchemy import create_engine
    import pymongo

    create_tables()
    
    myclient = pymongo.MongoClient("mongodb://localhost:27017")
    mydb = myclient['youtube']
    mycol = mydb["youtube data"]
  

    
    collection =mydb['youtube data']
    
    document_names = []
    
    for document in collection.find():
        document_names.append(document)
    mongodata=pd.DataFrame(document_names)
        
    channel_details =mongodata['channel_details']
    
    video_details=mongodata['video_data']
    
    comment_detail=mongodata['video_comments']
    
    channel_dat=[]
    for i in range(len(channel_details)):
        channel_dataframe=channel_details[i][0]
        channel_dat.append(channel_dataframe)
    channel_dataframe=pd.DataFrame(channel_dat)
    
        
    channel_id_playlist_id = channel_dataframe[['channel_id', 'playlist_id']]
    
#The extend() method in Python is used to append elements from an iterable 
#such as a list, tuple, or another iterable) to the end of an existing list
#It modifies the original list in place by adding elements from the iterable.
        
    video_dat=[]
    for i in range(len(video_details)):
        all_videos=video_details[i]
        video_dat.extend(all_videos)
    video_info=pd.DataFrame(video_dat)
    
    
    
    comment_dat=[]
    for i in range(len(comment_detail)):
        all_comments=comment_detail[i]
        comment_dat.extend(all_comments)
    comment_data=pd.DataFrame(comment_dat)
   
    mydb = pymysql.connect(
        host="localhost",
        user="root",
        # password="Rakul@9360721393",
        password="",
        autocommit=True)
    
    mycursor=mydb.cursor()
    mycursor.execute("SHOW DATABASES")
    mycursor.execute("USE youtubedata")
    
    #inserting channneldetails
    insert_channeldetails='''INSERT IGNORE INTO channel_data (channel_id,channel_name,
    total_video_count,channel_description, channel_status,subscribers,playlist_id)
    VALUES(%s,%s,%s,%s,%s,%s,%s)'''
    
    values=channel_dataframe.values.tolist()
    mycursor.executemany(insert_channeldetails,values)
    
    #inserting playlistid
    insert_playlistinfo='''INSERT IGNORE INTO playlist_details(channel_id,playlist_id)
    VALUES(%s,%s)'''

    values=channel_id_playlist_id.values.tolist()
    mycursor.executemany(insert_playlistinfo,values)
    
    #inserting channneldetails
    insert_videodata='''INSERT IGNORE INTO video_data(video_id,playlist_id,
    video_name,video_description,published_date,view_count,like_count,dislike_count,favorite_count,comment_count,duration,thumbnail,caption_status)
    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''

    values=video_info.values.tolist()
    mycursor.executemany(insert_videodata,values)
    
    #inserting channneldetails
    insert_commentdata='''INSERT IGNORE INTO comment_datas(comment_id,video_id,
    comment_text,comment_author, comment_published_date)
    VALUES(%s,%s,%s,%s,%s)'''

    values=comment_data.values.tolist()
    mycursor.executemany(insert_commentdata,values)

menu = ["Home", "Channel details", "SQL Data Warehouse","Spicy Questions","About Me"]
choice = st.sidebar.selectbox("Select an option", menu)
if choice == "Home":
    st.title("Welcome to the YouTube Data Warehousing App")
    st.write("This app allows you to collect and analyze data from multiple YouTube channel")
if choice=='Channel details':

    channel=st.text_input("Enter channel_id")
    submit=st.button('submit')

    if submit:
        c=channel_details(youtube,channel)
        st.dataframe(c)
        v=get_video_ids(youtube,c[0]['playlist_id'])
        # vds=[]
        # for i in v:
        #     vds.append(i[0])
        # st.write(vds)
        vd= video_data(youtube, v)
        st.dataframe(vd)
        cd=get_video_comments(youtube,v)
        st.dataframe(cd)
        all_data_info=get_all_data(youtube, channel,v)
        # st.write(all_data_info)
        st.header(':green[Data Collection]')
        insert_to_mongodb(all_data_info)
        st.write('successfull inserted to mongodb')
        
def app_sql():
    
    if choice=="SQL Data Warehouse":
        import_to_sql=st.button('Import_to_SQL')
        st.write("click this above button to import data")
        if import_to_sql:
            imported=insert_data_to_sql()
            st.write('inserted succcesfully')
            # st.experimental_rerun()
            
def main():
    if choice=="Spicy Questions":
        st.subheader("Select a  question!!")
        ques1 = '1.	What are the names of all the videos and their corresponding channels?'
        ques2 = '2.	Which channels have the most number of videos, and how many videos do they have?'
        ques3 = '3.	What are the top 10 most viewed videos and their respective channels?'
        ques4 = '4.	How many comments were made on each video, and what are their corresponding video names?'
        ques5 = '5.	Which videos have the highest number of likes, and what are their corresponding channel names?'
        ques6 = '6.	What is the total number of likes and dislikes for each video, and what are their corresponding video names?'
        ques7 = '7.	What is the total number of views for each channel, and what are their corresponding channel names?'
        ques8 = '8.	What are the names of all the channels that have published videos in the year 2022?'
        ques9 = '9.	What is the average duration of all videos in each channel, and what are their corresponding channel names?'
        ques10 = '10.Which videos have the highest number of comments, and what are their corresponding channel names?'
        question = st.selectbox('Queries!!',(ques1,ques2,ques3,ques4,ques5,ques6,ques7,ques8,ques9,ques10))
        clicked4 = st.button("Go..")
        
        if clicked4:
            mydb = pymysql.connect(
            host="localhost",
            user="root",
            # password="Rakul@9360721393",
            password="",
            autocommit=True)
            
            mycursor=mydb.cursor()
            mycursor.execute("SHOW DATABASES")
            mycursor.execute("USE youtubedata")
            
            if question == ques1:
                query = "select VIDEO_NAME,CHANNEL_NAME FROM VIDEO_DATA AS A INNER JOIN CHANNEL_dATA AS B ON A.PLAYLIST_ID=B.PLAYLIST_ID;"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques2:
                query = "select channel_name,total_video_count from channel_Data where total_video_count=(SELECT MAX(total_video_count) FROM channel_Data)"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques3:
                query = "select video_name,view_count,channel_name from video_DAta as a inner join channel_data as b on a.playlist_id=b.playlist_id order by view_count desc limit 10;"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques4:
                query = "select comment_count,video_name from video_Data order by comment_count desc"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques5:
                query = "select video_name,like_count,channel_name from video_data as a inner join channel_data as b on a.playlist_id=b.playlist_id where like_count=(select max(like_count) from video_data); "
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques6:
                query = "select like_count,dislike_count,video_name from video_data order by like_count asc"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques7:
                query = "select channel_name,sum(view_count) as total_video_count from video_Data as a inner join channel_Data as b on a.playlist_id=b.playlist_id group by b.channel_name order by sum(view_count);"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques8:
                query = "select published_Date,channel_name from video_Data as a inner join channel_data as b on a.playlist_id=b.playlist_id where published_DAte=2022;"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques9:
                query = "select channel_name,avg(duration) from video_Data as a inner join channel_Data as b on a.playlist_id=b.playlist_id group by b.channel_name;"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            elif question == ques10:
                query = "select video_name,comment_count,channel_name from video_data as a inner join channel_Data as b on a.playlist_id=b.playlist_id where comment_count=(select max(comment_count) from video_Data);"
                mycursor.execute(query)
                results =mycursor.fetchall()
                st.dataframe(results)
            
#  the code structure using if __name__ == '__main__': allows you to define and execute 
#  specific code (e.g., functions, initialization tasks, etc.) that should only be executed when the script is run directly as the main program
# When a script is imported as a module, the Python interpreter executes all the top-level code 
# in that script, including function definitions and other initialization tasks. Placing the main program code
# inside the if __name__ == '__main__': block ensures that it will only be
# executed when the script is run directly, avoiding unintended execution when the script is imported as a module.
if __name__ == '__main__':
    main()
    app_sql()
                

                
if choice=="About Me":
    st.write('This project is done by Abinaya Selvaraj')
    URL="https:www.linkedin.com/in/abinaya-selvaraj-808464201"
    st.markdown(f"Click [here]({URL}) to visit the linkedin website to know about me.")
