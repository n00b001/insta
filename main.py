import os
import random
import re
import shutil
import threading
import traceback
from lxml import html

import requests
from time import sleep, time

import schedule as schedule
from InstagramAPI import InstagramAPI
from datetime import datetime

uploading = False

start_range_like = 5
end_range_like = 30

start_range_follow = 50
end_range_follow = 160

start_range_unfollow = 30
end_range_unfollow = 100

WHEN_TO_STOP_FOLLOWING = 60 * 60 * 24

FAILURE_SLEEP_TIME = 30*60

lock = threading.Lock()


def sleep_if_needed(json, return_val, func_type):
    try:
        if "try again." in json["message"]:
            print("Rate limited for {}".format(func_type))
            sleep_random(FAILURE_SLEEP_TIME, FAILURE_SLEEP_TIME * 2)
            return True
    except:
        pass
    try:
        if "error" in json["message"]:
            print("Some error for {}".format(func_type))
            sleep_random(FAILURE_SLEEP_TIME, FAILURE_SLEEP_TIME * 2)
            return True
    except:
        pass
    try:
        if "Blocked" in json["feedback_title"]:
            print("Blocked for {}".format(func_type))
            sleep_random(FAILURE_SLEEP_TIME, FAILURE_SLEEP_TIME * 2)
            return True
    except:
        pass
    if not return_val:
        print("ReturnVal was false for {}, sleeping for 1 min".format(func_type))
        sleep(60)
        if "upload" == func_type:
            api.logout()
            api.login()
            return True
    return False


api = InstagramAPI("xfanth", ")
while True:
    try:
        ret_val = api.login()
        if not sleep_if_needed(api.LastJson, ret_val, "login"):
            break
    except:
        pass

people_to_keep = set()
im_following = set()
following_me = set()
removed = set()


def get_random_time(start_range, end_range):
    return random.uniform(start_range, end_range)


def sleep_random(start_range, end_range):
    sleep_time = get_random_time(start_range, end_range)
    print("Sleeping for {} seconds...".format(sleep_time))
    sleep(sleep_time)


def follow(param, user_info):
    while uploading:
        print("Will not follow while uploading, sleeping for 5 mins...")
        sleep(60 * 5)
    while True:
        val = api.follow(param)
        if not sleep_if_needed(api.LastJson, val, "follow"):
            break
    print("Following: {}".format(user_info["user"]["full_name"]))
    now = int(time())
    with lock:
        update_followings()
        with open("following.txt", "a") as f:
            f.write(str(param) + "," + str(now) + "\n")
    sleep_random(start_range_follow, end_range_follow)


def follow_popular():
    tags = ["f4f", "follow4follow", "followforfollow", "london", "uk", "purfleet", "england"]
    while True:
        for tag in tags:
            while True:
                val = api.getHashtagFeed(tag)
                json = api.LastJson

                if not sleep_if_needed(json, val, "getHashTagFeed follow"):
                    break
            json = json["items"]
            for content in json:
                try:
                    if content["user"]["pk"] in im_following:
                        continue
                    if content["user"]["pk"] in following_me:
                        continue

                    while True:
                        val = api.getUsernameInfo(content["user"]["pk"])
                        user_info = api.LastJson

                        if not sleep_if_needed(user_info, val, "get user info, follow"):
                            break

                    followers = float(user_info["user"]["follower_count"])
                    following = float(user_info["user"]["following_count"])

                    ratio = (1 + followers) / (following + 1)
                    if ratio < 1:
                        follow(user_info["user"]["pk"], user_info)

                        # api.like()
                except Exception as e:
                    traceback.print_exc()
                    print(e)


def like(param):
    while uploading:
        print("Will not like while uploading, sleeping for 5 mins...")
        sleep(60 * 5)
    while True:
        val = api.like(param)
        if not sleep_if_needed(api.LastJson, val, "like"):
            break
    print("Liked: {}".format(param))
    sleep_random(start_range_like, end_range_like)


def like_popular():
    tags = ["l4l", "likeforfollow", "like4follow", "like4like",
            "likeforlike", "london", "uk", "purfleet", "england"]
    while True:
        for tag in tags:
            while True:
                val = api.getHashtagFeed(tag)
                json = api.LastJson

                if not sleep_if_needed(json, val, "get feed, like"):
                    break
            json = json["items"]
            for content in json:
                try:
                    like(content["pk"])
                except Exception as e:
                    traceback.print_exc()
                    print(e)


def unfollow_id(id):
    while uploading:
        print("Will not unfollow while uploading, sleeping for 5 mins...")
        sleep(60 * 5)
    while True:
        val = api.unfollow(id)
        if not sleep_if_needed(api.LastJson, val, "unfollow"):
            break
    print("Unfollowing {}".format(id))
    sleep_random(start_range_unfollow, end_range_unfollow)


def delete_line(person):
    with lock:
        with open("following.txt", "r") as f:
            f.seek(0)
            lines = f.readlines()
        os.remove("following.txt")
        open("following.txt","a").close()
        with open("following.txt", "w") as f:
            f.writelines([x for x in lines if str(x).strip() != str(person)])
    removed.add(person)
            # for l in lines:
            #     if str(l).strip() != str(person):
            #         f.write(l)


def unfollow():
    global removed
    while True:
        try:
            with lock:
                update_followings()
                if os.path.exists("following.txt"):
                    with open("following.txt", "r") as f:
                        f.seek(0)
                        people = f.readlines()
                        people = [str(p).strip().split(",") for p in people]
                        people = [[int(p[0]), int(p[1])] for p in people]

            for per in im_following:
                try:
                    person = [p for p in people if p[0] == per]
                    if len(person) == 0:
                        continue
                    if type(person[0]) == list:
                        person = person[0]
                    if person[0] not in im_following:
                        if person[0] not in removed:
                            delete_line(person[0])
                        continue

                    if person[0] not in removed:
                        if len(person) > 1:
                            if time() - WHEN_TO_STOP_FOLLOWING > person[1] \
                                    or person[0] in following_me:
                                unfollow_id(person[0])
                                delete_line(person[0])
                        elif person[0] not in people_to_keep:
                            unfollow_id(person[0])
                            delete_line(person[0])
                except Exception as e:
                    traceback.print_exc()
                    print(e)
                    print("Trying to unfollow: {}".format(person))
            removed = set()
            print("PROCESSED UNFOLLOWS")
            sleep_random(start_range_like, end_range_like)
        except Exception as e:
            sleep_random(start_range_like, end_range_like)
            traceback.print_exc()
            print(e)


def get_popular_tags():
    page = requests.get('https://www.tagblender.net/')
    tree = html.fromstring(page.content)
    tags = tree.xpath('//div[@id="tags6"]/text()')
    return_tags = str(tags[0])
    # whitespace_rep = re.compile(re.escape('^[\s\\t\\n ]*'), re.IGNORECASE)
    iphone_rep = re.compile(r'#[a-z]*iphone[a-z]* *', re.IGNORECASE)
    girl_rep = re.compile(r'#[a-z]*girl[a-z]* *', re.IGNORECASE)
    return_tags = return_tags.lstrip().rstrip()
    return_tags = re.sub(iphone_rep, "", return_tags)
    return_tags = re.sub(girl_rep, "", return_tags)
    # return_tags = iphone_rep.sub("", return_tags)
    # return_tags = girl_rep.sub("", return_tags)
    return return_tags


def upload():
    try:
        global uploading
        files = os.listdir("to-upload")
        if len(files) > 0:
            uploading = True
            rand_pic = random.choice(files)
            shutil.move("to-upload/" + rand_pic, "uploaded/" + rand_pic)
            while True:
                caption = str(rand_pic).replace("__", "\n").replace("_", " ").replace(".jpg", "")
                popular_tags = get_popular_tags()
                caption += "\n.\n.\n.\n.\n.\n" + popular_tags
                print("Uploading: {}".format(caption))
                val = api.uploadPhoto("uploaded/" + rand_pic, caption=caption)
                if not sleep_if_needed(api.LastJson, val, "upload"):
                    break
                api.logout()
                while True:
                    val = api.login()
                    if not sleep_if_needed(api.LastJson, val, "login"):
                        break
            print("Uploaded {}".format(rand_pic))
    finally:
        uploading = False
        set_schedule()


def set_schedule():
    schedule_time = "{}:{}".format(int(random.uniform(8, 12)), int(random.uniform(0, 59)))
    num = int(random.uniform(2,4))
    daydic = {
        1:"monday",
        2:"tuesday",
        3:"wednesday",
        4:"thursday",
        5:"friday"
    }
    day = getattr(schedule.every(), daydic[num])
    day.at(schedule_time).do(upload)
    print("Schedule set for: {} on {}".format(schedule_time, daydic[num]))


def uploader():
    set_schedule()
    # sleep_random(60*60*24*6, 60*60*24*9)
    while True:
        schedule.run_pending()
        sleep(60)


def save_follow_count():
    with open("followers_stats.csv","a") as f:
        f.write(str(len(following_me)) + "," + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
    with open("following_stats.csv","a") as f:
        f.write(str(len(im_following)) + "," + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")


def update_followings_thread():
    while True:
        update_followings()
        sleep(60*5)


def update_followings():
    global im_following, following_me
    try:
        while True:
            val = api.getTotalSelfFollowings()
            # im_following_temp = api.LastJson
            if not sleep_if_needed(api.LastJson, val, "following"):
                im_following = [x["pk"] for x in val]
                break
        while True:
            val = api.getTotalSelfFollowers()
            # following_me_temp = api.LastJson
            if not sleep_if_needed(api.LastJson, val, "followers"):
                following_me = [x["pk"] for x in val]
                save_follow_count()
                break
    except Exception as e:
        traceback.print_exc()
        print(e)


def main():
    global people_to_keep

    update_followings()

    with open("im_following.txt", "r") as f:
        people_to_keep = f.readlines()
    people_to_keep = [int(str(x).strip()) for x in people_to_keep]

    # with open("im_following.txt", "w") as f:
    #     f.writelines([str(x) + "\n" for x in im_following])
    #
    # return

    t1 = threading.Thread(target=follow_popular)
    t1.start()

    t2 = threading.Thread(target=unfollow)
    t2.start()

    t3 = threading.Thread(target=like_popular)
    t3.start()

    t4 = threading.Thread(target=uploader)
    t4.start()

    t5 = threading.Thread(target=update_followings_thread)
    t5.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()
    t5.join()


if __name__ == '__main__':
    main()
