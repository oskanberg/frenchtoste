#!/usr/bin/env python

import praw

USER = "french_toste"
PASS = "ftftftftftft"

class FrenchToste(object):

    def __init__(self):
        self.name       = "FrenchToste"
        self.username   = USER
        self.password   = PASS
        self.r          = praw.Reddit(user_agent=self.name) 
        #print "Logging in ... "
        #self.r.login(self.username, self.password)
    
    def get_comment_suggestions(self, subreddit, number):
        print "Getting posts in /r/%s ... " % subreddit
        posts = self.r.get_subreddit(subreddit).get_hot(limit=number)
        duplicates = self.search_for_duplicates(posts.next())
        if duplicates:
            print "Duplicates:", [str(a) for a in duplicates]
            self.apply_filters(duplicates)
        else:
            print "No duplicates."
            return

    def search_for_duplicates(self, post):
        print "Checking for duplicates:\n%s" % post.url
        try:
            # will fail if result is len 1
            duplicates = list(self.r.search(post.url))
        except Exception, e:
            return
            
        if post in duplicates:
            print "Removing %s from duplicates." % str(post)
            duplicates.remove(post)
        return duplicates
    
    def apply_filters(self, posts):
        for post in posts:
            if "x-post" in post.title or "xpost" in post.title:
                print "Removing %s because it is a x-post." % post
                posts.remove(post)
        

ft = FrenchToste()
for sr in ["funny", "all", "pics", "random"]:
    ft.get_comment_suggestions(sr, 1)

    
    
