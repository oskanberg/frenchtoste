#!/usr/bin/env python

from multiprocessing import Process, Lock
import praw
import time
import sys
import os
import random

lock = Lock()

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
    
    def __init__(self, dataFile, description):
        self.debug          = True
        self.db             = dataFile
        self.description    = description
    
    def store_suggestion(self, suggestion):
        # stores in new line as <submission>:<comment>:<prospect>
        with self.lock:
            with open(self.db, "a") as f:
                self.debugPrint("Storing suggestion.")
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
                time.sleep(5)
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
        r = praw.Reddit(self.description)
        while True:
            self.debugPrint('Searching ...')
            try:
                post = r.get_subreddit('random').get_hot(limit=1)
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
                    self.debugPrint("Comment score too low.")
                    continue
                else:
                    self.store_suggestion(suggestion)
            self.space()
    
    def set_output_file(self, outputFile):
        self.db = outputFile


class FrenchToste(object):
    
    def __init__(self, brains, username, password, description, dataFile):
        self.lastPostTime   = 0
        self.lock      = lock
        self.username  = username
        self.password  = password
        self.r         = praw.Reddit(description)
        self.brains    = [FrenchTosteBrain(dataFile, description) for i in xrange(brains)]
    
    def find_suggestions(self, threshold, outputFile):
        print "Outputting to: %s" % os.path.join(os.getcwd(), outputFile)
        with self.lock:
            try:
                with open(outputFile, "a+") as f: pass
            except IOError as e:
                print "IO Error:", e
        for brain in self.brains:
            brain.set_output_file(outputFile)
            Process(target = brain.intelligent_search, args = (50,)).start()
    
    def post_comment(self, submissionID, commentID):
        while time.time() - self.lastPostTime <= 600:
            print '%ss ...' % (600 - (time.time() - self.lastPostTime))
            time.sleep(1)
        print 'Regenerating comment ...'
        submission = self.r.get_submission(submission_id = submissionID)
        commmentBody = self.r.get_submission(submission_id = commentID).comments[0].body.replace('&gt;', '> ')
        time.sleep(5)
        print 'Logging in ...'
        self.r.login(self.username, self.password)
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
    
    def __init__(self, inputFile, ft):
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
    if os.name != 'nt':
        print 'Proxy:'
        os.environ['http_proxy'] = raw_input()
    DATA = os.path.abspath(os.path.join(os.path.curdir, 'suggestions'))
    print 'Username:'
    USER = raw_input()
    print 'Password:'
    PASS = raw_input()
    DESCRIPTION = 'albert_hindsight v0.2 by /user/blackmirth: scans for popular information in reposts to consolidate information.'
    
    ft = FrenchToste(1, USER, PASS, DESCRIPTION, DATA)
    sr = SuggestionReader(DATA, ft)
    ft.find_suggestions(50, DATA)
    sr.loop()

if __name__ == '__main__':
    main()
