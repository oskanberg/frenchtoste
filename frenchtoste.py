#!/usr/bin/env python

#TODO: - when there are many suggestions, display all? select highest?
#      - convert &gt; to "> "
#      - multithreading.py - searcher and queue of possibilies

import praw
import time

USER = "french_toste"
PASS = "ftftftftftft"

class CommentSuggestion:
    
    def __init__(self, originalCommentObject, submission):
        self.commentBody        = originalCommentObject.body
        self.commentAuthor      = originalCommentObject.author
        self.originalSubmission = originalCommentObject.submission
        self.originalScore      = originalCommentObject.score
        self.newSubmission      = submission

class FrenchToste(object):
    
    def __init__(self):
        self.lastPostTime   = time.time()
        self.name           = "FrenchToste"
        self.username       = USER
        self.password       = PASS
        self.r              = praw.Reddit(user_agent=self.name) 
        print "Logging in ... "
        self.r.login(self.username, self.password)
    
    def get_comment_suggestions_for_post(self, post):
        print "Getting suggestions for:\n", str(post)
        duplicates = self.search_for_duplicates(post)
        if len(duplicates) > 0:
            duplicates = self.apply_post_filters(duplicates)
            suggestions = []
            for dup in duplicates:
                comments = list(dup.comments)
                if len(comments) > 0:
                    try:
                        comments = sorted(comments, key=lambda x: x.score, reverse=True)
                    except Exception, e:
                        print "Comments not loading quick enough. Sleeping for 10s."
                        time.sleep(10)
                        print "Trying again. Hope it works."
                        comments = list(dup.comments)
                        comments = sorted(comments, key=lambda x: x.score, reverse=True)
                    suggestion = CommentSuggestion(comments[0], post)
                    suggestions.append(suggestion)
                    suggestions = self.apply_comment_filters(suggestions)
            if not suggestions:
                print "No suggestions."
            return suggestions
        else:
            print "No duplicates."
            return []
    
    def search_for_duplicates(self, post):
        print "Checking for duplicates:\n%s" % post.url
        try:
            # will fail if result is len 1
            duplicates = list(self.r.search(post.url))
        except Exception, e:
            return []
        if post in duplicates:
            print "Removing original post ..."
            duplicates.remove(post)
        return duplicates
    
    def apply_post_filters(self, posts):
        print "Applying post filters ..."
        for post in posts:
            if "x-post" in post.title or "xpost" in post.title:
                print "Removing xpost."
                posts.remove(post)
        return posts
    
    def apply_comment_filters(self, comments):
        print "Applying comment filters ..."
        for comment in comments:
            if comment.originalSubmission.author == comment.commentAuthor:
                print "Removing self comment."
                comments.remove(comment)
        return comments
                
    def prompt(self):
        self.space()
        print "Submit comment? [y/N]"
        while True:
            ans = raw_input()
            if not ans:
                return resp
            if ans not in ['y', 'Y', 'n', 'N']:
                print 'please enter y or n.'
                continue
            if ans == 'y' or ans == 'Y':
                return True
            if ans == 'n' or ans == 'N':
                return False
                
    def suggest(self, suggestion):
        self.space()
        print "############## Suggestion ##############"
        print "commentBody: %s\nnewSubmission: %s\noriginalSubmission: %s\noriginalScore: %s" \
            % (suggestion.commentBody, suggestion.newSubmission, suggestion.originalSubmission, suggestion.originalScore)
        if self.prompt():
            self.post_comment(suggestion)
        self.space()
                    
    def space(self):
        print "\n"
    
    def post_comment(self, comment):
        while self.lastPostTime - time.time() >= 600:
            print "%ss ..." % ((time.lastPostTime - time.time()) - 600)
            time.sleep(1)
        print "Posting comment ..."
        comment.commentBody = comment.commentBody.replace("&gt;", "> ")
        try:
            comment.newSubmission.add_comment(comment.commentBody)
        except Exception, e:
            print "Posting failed. You might be posting too often. Retrying."
            self.lastPostTime = time.time()
            self.post_comment(comment)
        self.lastPostTime = time.time()
        print "Done."
    
    def intelligent_search(self, threshold):
        print "Warning: this might take a long time and will continue indefinitely."
        while True:
            print "Searching ..."
            post        = self.r.get_subreddit("random").get_hot(limit=1)
            suggestions = self.get_comment_suggestions_for_post(post.next())
            for suggestion in suggestions:
                if suggestion.originalScore < threshold:
                    continue
                else:
                    self.suggest(suggestion)
            self.space()
        
    def check_subreddits(self, subreddits):
        for sr in subreddits:
            post        = self.r.get_subreddit(sr).get_hot(limit=1)
            suggestions = self.get_comment_suggestions_for_post(post.next())
            for suggestion in suggestions:
                self.suggest(suggestion)
            self.space()

ft = FrenchToste()
#ft.check_subreddits(["pics", "funny", "all", "random"])
ft.intelligent_search(10)

