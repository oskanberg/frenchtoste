#!/usr/bin/env python

#TODO: - when there are many suggestions, display all? select highest?
#      - multithreading.py - searcher and queue of possibilies

from multiprocessing import Process, Lock
import praw
import time
import sys
import os
import random

DATA = os.path.abspath(os.path.join(os.path.curdir, 'suggestions'))
#USER = 'french_toste'
USER = 'albert_hindsight'
#PASS = 'ftftftftftft'
PASS = 'albert_hindsight'
DESCRIPTION = 'albert_hindsight v0.1 by /u/blackmirth: scans for popular information posted in reposts to consolidate information.'


class CommentSuggestion(object):
    
    def __init__(self, originalCommentObject, submission):
        # Especially stringent so it can get pickled
        self.commentID    = str(originalCommentObject.permalink)
        self.submissionID = str(submission.id)
        self.prospect     = int(self.getSubmissionObject().score)
    
    def getCommentObject(self):
        repickler = praw.Reddit('repickler')
        for attempt in xrange(5):
            try:
                obj = repickler.get_submission(submission_id = self.commentID).comments[0]
                return obj
            except Exception, e:
                time.sleep(random.randint(10))

    def getSubmissionObject(self):
        repickler = praw.Reddit('repickler')
        for attempt in xrange(5):
            try:
                obj = repickler.get_submission(submission_id = self.submissionID)
                return obj
            except Exception, e:
                time.sleep(random.randint(10))


class FrenchTosteBrain(object):
    
    def __init__(self, r, lock):
        self.lock           = lock
        self.debug          = True
        self.db             = DATA
        self.r              = r
    
    def store_suggestion(self, suggestion):
        # stores in new line as <submission>:<comment>:<prospect>
        with self.lock:
            with open(self.db, "a") as f:
                f.write("%s;%s;%s\n" % (suggestion.submissionID, suggestion.commentID, suggestion.prospect))
        
    def debugPrint(self, msg):
        if self.debug:
            print msg
        
    def get_comment_suggestions_for_post(self, post):
        self.debugPrint('Getting suggestions for:\n%s' % str(post))
        duplicates = self.search_for_duplicates(post)
        if len(duplicates) > 0:
            duplicates = self.apply_post_filters(duplicates)
            suggestions = []
            for dup in duplicates:
                try:
                    comments = list(dup.comments)
                except Exception, e:
                    self.debugPrint('Forbidden. Ignoring.')
                    self.debugPrint(e)
                    continue
                if len(comments) > 0:
                    try:
                        comments = sorted(comments, key=lambda x: x.score, reverse=True)
                    except Exception, e:
                        self.debugPrint('Comments not loading correctly. Ignoring.')
                        self.debugPrint(e)
                        continue
                    suggestion = CommentSuggestion(comments[0], post)
                    suggestions.append(suggestion)
                    suggestions = self.apply_comment_filters(suggestions)
            if not suggestions:
                self.debugPrint('No suggestions.')
            suggestions = sorted(suggestions, key=lambda x: x.getCommentObject().score, reverse=True)
            return suggestions
        else:
            self.debugPrint('No duplicates.')
            return []
    
    def search_for_duplicates(self, post):
        self.debugPrint('Checking for duplicates:\n%s' % post.url)
        try:
            # will fail if result is len 1
            duplicates = list(self.r.search(post.url))
        except Exception, e:
            return []
        if post in duplicates:
            self.debugPrint('Removing original post ...')
            duplicates.remove(post)
        return duplicates
    
    def apply_post_filters(self, posts):
        self.debugPrint('Applying post filters ...')
        for post in posts:
            if 'x-post' in post.title or 'xpost' in post.title:
                self.debugPrint('Removing xpost.')
                posts.remove(post)
        return posts
    
    def apply_comment_filters(self, comments):
        self.debugPrint('Applying comment filters ...')
        for comment in comments:
            co = comment.getCommentObject()
            if co.submission.author == co.author:
                self.debugPrint('Removing self comment.')
                comments.remove(comment)
        return comments
                
    def space(self):
        self.debugPrint('\n')
    
    def intelligent_search(self, threshold):
        self.debugPrint('Warning: this might take a long time and will continue indefinitely.')
        while True:
            self.debugPrint('Searching ...')
            try:
                post = self.r.get_subreddit('random').get_hot(limit=1)
            except Exception, h:
                self.debugPrint("HTTP error:\n" % h)
                self.debugPrint("Ignoring.")
                continue
            try:
                post = post.next()
            except Exception, e:
                self.debugPrint("Error getting next post.")
            suggestions = self.get_comment_suggestions_for_post(post)
            for suggestion in suggestions:
                if suggestion.getCommentObject().score < threshold:
                    continue
                else:
                    self.store_suggestion(suggestion)
            self.space()
    
    def set_output_file(self, outputFile):
        self.db = outputFile


class FrenchToste(object):
    
    def __init__(self, brains, lock):
        self.lastPostTime   = 0
        self.username  = USER
        self.password  = PASS
        self.r         = praw.Reddit(DESCRIPTION)
        self.brains    = [FrenchTosteBrain(self.r, lock) for i in xrange(brains)]
        print 'Logging in ...'
        self.r.login(self.username, self.password)
    
    def find_suggestions(self, threshold, outputFile):
        print "Outputting to: %s" % os.path.join(os.getcwd(), outputFile)
        try:
            with open(outputFile, "a+") as f: pass
        except IOError as e:
            print "IO Error:", e
        for brain in self.brains:
            brain.set_output_file(outputFile)
            Process(target = brain.intelligent_search, args = (threshold,)).start()
    
    def post_comment(self, submissionID, commentID):
        while time.time() - self.lastPostTime <= 600:
            print '%ss ...' % (600 - (time.time() - self.lastPostTime))
            time.sleep(1)
        print 'Regenerating comment ...'
        submission = self.r.get_submission(submission_id = submissionID)
        commmentBody = self.r.get_submission(submission_id = commentID).comments[0].body.replace('&gt;', '> ')
        time.sleep(5)
        print 'Posting comment ...'
        try:
            comment.getSubmissionObject().add_comment(newComment)
        except Exception, e:
            print 'Posting failed. You might be posting too often. Retrying.'
            print e
            self.lastPostTime = time.time()
            self.post_comment(submissionID, commentID)
        self.lastPostTime = time.time()
        print 'Done.'


class SuggestionReader(object):
    
    def __init__(self, inputFile, ft, lock):
        self.inputFile = inputFile
        self.ft        = ft
        self.lock      = lock
    
    def space(self):
        print '\n'

    def prompt(self):
        self.space()
        print 'Submit comment? [y/N]'
        while True:
            ans = raw_input()
            if not ans:
                return resp
            if ans not in ['y', 'Y', 'n', 'N']:
                print 'got \"%s\"' % ans
                print 'please enter y or n.'
                continue
            if ans == 'y' or ans == 'Y':
                return True
            if ans == 'n' or ans == 'N':
                return False

    def suggest(self, so, co):
        self.space()
        print '############## Suggestion ##############'
        print 'commentBody: %s'         % co.body
        print 'newSubmission: %s'       % so
        print 'originalSubmission: %s'  % co.submission
        print 'originalScore: %s'       % co.score
        if self.prompt():
            self.ft.post_comment(suggestion)
        self.space()
    
    def load_suggestion_strings(self):
        print self.inputFile
        with self.lock:
            with open(self.inputFile, "r") as f:
                sugs = []
                for sug in f:
                    sugs.append(sug)
        return sugs
        
    def loop(self):
        while True:
            time.sleep(10)
            os.system(['clear', 'cls'][os.name == 'nt'])
            if os.stat(self.inputFile).st_size > 0:
                suggestions = self.load_suggestion_strings()
                for suggestion in suggestions:
                    args = suggestion.split(";")
                    self.ft.post_comment(args[0], args[1])
            else:
                print "No items available yet."

    
def main():
    lock = Lock()
    ft = FrenchToste(0, lock)
    sr = SuggestionReader(DATA, ft, lock)
    ft.find_suggestions(50, DATA)
    sr.loop()
    #r = praw.Reddit(DESCRIPTION)
    #r.login(USER,PASS)
    #a = r.get_subreddit("random").get_hot(1)
    #a.next().add_comment("hello")

if __name__ == '__main__':
    main()
