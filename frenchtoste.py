#!/usr/bin/env python

from multiprocessing import Process, Lock
import praw
import time
import sys
import os
import random

lock = Lock()
DEBUG = True 

class CommentSuggestion(object):
    
    def __init__(self, originalCommentObject, submission):
        # Especially stringent so it can get pickled
        self.commentID    = originalCommentObject.permalink.encode('ascii', 'ignore')
        self.submissionID = submission.id.encode('ascii', 'ignore')
        self.prospect     = int(self.getSubmissionObject().score)
    
    def getCommentObject(self):
        repickler = praw.Reddit('repickler')
        for attempt in xrange(5):
            try:
                obj = repickler.get_submission(submission_id = self.commentID).comments[0]
                return obj
            except Exception, e:
                time.sleep(random.randint(0, 5))

    def getSubmissionObject(self):
        repickler = praw.Reddit('repickler')
        for attempt in xrange(5):
            try:
                obj = repickler.get_submission(submission_id = self.submissionID)
                return obj
            except Exception, e:
                time.sleep(random.randint(0, 5))


class FrenchTosteBrain(object):
    
    def __init__(self, dataFile, description, completeFile):
        self.debug          = DEBUG
        self.db             = dataFile
        self.description    = description
        self.lock           = lock
        self.completed      = completeFile
    
    def hacky_sleep(self, length):
        with self.lock:
            time.sleep(length)
            time.sleep(random.randint(0, 5))
            
    def load_complete(self):
        if not os.path.exists(self.completed):
            with open(self.completed, 'w') as f: pass
        with self.lock:
            with open(self.completed, 'r') as f:
                complete = []
                for c in f:
                    c = c.strip()
                    complete.append(c)
        return complete
    
    def store_complete(self, complete): 
        with self.lock:
            with open(self.completed, 'a') as f:
                f.write('%s\n' % complete)
    
    def load_suggestion_strings(self):
        with self.lock:
            with open(self.db, 'r') as f:
                sugs = []
                for sug in f:
                    sugs.append(sug.strip())
        return sugs

    def store_suggestion(self, suggestion, kind):
        if kind == 'ADD':
            # stores in new line as <submission>;<comment>;<prospect>
            sug = '%s;%s;%s;ADD\n' % (suggestion.submissionID, suggestion.commentID, suggestion.prospect)
        elif kind == 'DEL':
            sug = '%s;DEL\n' % (suggestion)
        if sug not in self.load_suggestion_strings():
            with self.lock:
                self.debug_print('Storing suggestion.')
                with open(self.db, 'a') as f:
                    f.write(sug)
        
    def debug_print(self, msg):
        if self.debug:
            try:
                print msg
            except Exception, e:
                print '[exception printing value. Probably Unicode]'
        
    def get_comment_suggestions_for_post(self, post):
        self.debug_print('Getting suggestions for:\n%s' % str(post))
        duplicates = self.search_for_duplicates(post)
        if len(duplicates) > 0:
            duplicates = self.apply_post_filters(duplicates)
            suggestions = []
            for dup in duplicates:
                self.hacky_sleep(2)
                try:
                    comments = list(dup.comments)
                except Exception, e:
                    self.debug_print('Forbidden. Ignoring.')
                    self.debug_print(e)
                    continue
                if len(comments) > 0:
                    try:
                        comments = sorted(comments, key=lambda x: x.score, reverse=True)
                    except Exception, e:
                        self.debug_print('Comments not loading correctly. Ignoring.')
                        self.debug_print(e)
                        continue
                    suggestion = CommentSuggestion(comments[0], post)
                    suggestions.append(suggestion)
                    suggestions = self.apply_comment_filters(suggestions)
            if not suggestions:
                self.debug_print('No suggestions.')
            suggestions = sorted(suggestions, key=lambda x: x.getCommentObject().score, reverse=True)
            return suggestions
        else:
            self.debug_print('No duplicates.')
            return []
    
    def search_for_duplicates(self, post):
        self.debug_print('Checking for duplicates:\n%s' % post.url)
        r = praw.Reddit(self.description)
        self.hacky_sleep(2)
        dup = r.search(post.url)
        try:
            # will fail if result is len 1
            duplicates = list(dup)
        except Exception, e:
            self.debug_print(e)
            return []
        if post in duplicates:
            self.debug_print('Removing original post ...')
            duplicates.remove(post)
        return duplicates
    
    def apply_post_filters(self, posts):
        self.debug_print('Applying post filters ...')
        for post in posts:
            t = post.title.lower()
            if 'x-post' in t or 'xpost' in t or 'x post' in t or 'crosspost' in t or 'cross post' in t:
                self.debug_print('Removing xpost.')
                posts.remove(post)
        return posts
    
    def apply_comment_filters(self, comments):
        self.debug_print('Applying comment filters ...')
        for comment in comments:
            co = comment.getCommentObject()
            try:
                if co.submission.author == co.author:
                    self.debug_print('Removing self comment.')
                    comments.remove(comment)
            except Exception,e:
                self.debug_print(e)
                comments.remove(comment)
        return comments

    def scrutinise_posts(self, username):
        print 'Scrutinising posts.'
        r = praw.Reddit(self.description)
        redditor = r.get_redditor(username)
        self.hacky_sleep(2)
        posts = list(redditor.get_comments(limit = 100))
        for post in posts:
            if post.score < 0:
                self.hacky_sleep(2)
                print 'DELETE THIS:'
                print post.permalink.encode('ascii', 'ignore')
                self.store_suggestion(post.permalink.encode('ascii', 'ignore'), 'DEL')
        # we really don't need to do this often.
        time.sleep(100)
        
    def intelligent_search(self, threshold):
        self.debug_print('Warning: this might take a long time and will continue indefinitely.')
        r = praw.Reddit(self.description)
        coolOffMarker = 0
        postLimit = 100
        subreddit = 'all'
        while True:
            self.debug_print('Searching ...')
            self.hacky_sleep(2)
            try:
                posts = r.get_subreddit(subreddit).get_hot(limit = postLimit)
            except Exception, h:
                self.debug_print('HTTP error:\n%s' % h)
                self.debug_print('Ignoring.')
                continue
            try:
                posts = list(posts)
            except Exception, e:
                self.debug_print(e)
            allProcessed = True
            for post in posts:
                if post.id not in self.load_complete():
                    allProcessed = False
                    self.store_complete(post.id)
                    suggestions = self.get_comment_suggestions_for_post(post)
                    for suggestion in suggestions:
                        if suggestion.getCommentObject().score < threshold:
                            self.debug_print('Comment score too low.')
                            continue
                        else:
                            self.store_suggestion(suggestion, 'ADD')
                else:
                    self.debug_print('Post has already been processed.')
            
            # if we've processed everything in /r/all, cool off for 
            # 300s to let it repopulate. Search /r/random meanwhile
            if allProcessed:
                self.debug_print('/r/all exhausted. Searching /r/random ...')
                subreddit = 'random'
                postLimit = 3
                coolOffMarker = time.time()
            if subreddit == 'random' and time.time() - coolOffMarker > 300:
                self.debug_print('Resuming /r/all search ...')
                postLimit = 100
                subreddit = 'all'
            elif subreddit == 'random' and time.time() - coolOffMarker < 300:
                self.debug_print("%0.0fs until /r/all resume." % (300 - (time.time() - coolOffMarker)))
    
    def set_output_file(self, outputFile):
        self.db = outputFile


class FrenchToste(object):
    
    def __init__(self, brains, username, password, description, dataFile, completeFile):
        self.lastPostTime   = 0
        self.lock      = lock
        self.username  = username
        self.password  = password
        self.r         = praw.Reddit(description)
        self.brains    = [FrenchTosteBrain(dataFile, description, completeFile) for i in xrange(brains + 1)]
    
    def hacky_sleep(self, length):
        with self.lock:
            print 'Sleeping %d ...' % length
            time.sleep(length)
            
    def find_suggestions(self, threshold, outputFile):
        print 'Outputting to: %s' % os.path.join(os.getcwd(), outputFile)
        with self.lock:
            try:
                with open(outputFile, 'a+') as f: pass
            except IOError as e:
                print 'IO Error:', e
        for brain in self.brains[:1]:
            brain.set_output_file(outputFile)
            Process(target = brain.intelligent_search, args = (50,)).start()
            time.sleep(random.randint(0,10))
        Process(target = self.brains[-1].scrutinise_posts, args = (self.username,)).start()

    def delete_comment(self, commentURL, retries):
        print 'Deleting %s' % commentURL
        try:
            comment = self.r.get_submission(submission_id = commentURL).comments[0]
        except IndexError, e:
            print 'Comment does not exist. Cache likely has not updated.'
            return True
        print 'logging in ...'
        self.hacky_sleep(5)
        try:
            self.r.login(self.username, self.password)
            self.hacky_sleep(5)
            comment.delete()
        except Exception, e:
            print 'Failed to delete: '
            print e
            if retries > 0:
                print 'Retrying delete ...'
                self.delete_comment(commentURL, retries - 1)
            else:
                print 'Complete failure to delete.'
        return True
        
    def post_comment(self, submissionID, commentID, retries):
        while time.time() - self.lastPostTime <= 600:
            sys.stdout.write('\r%ss ...' % (600 - (time.time() - self.lastPostTime)))
            sys.stdout.flush()
            time.sleep(1)
        print 'Regenerating comment ...'
        self.hacky_sleep(2)
        try:
            submission = self.r.get_submission(submission_id = submissionID)
            self.hacky_sleep(2)
            commentBody = self.r.get_submission(submission_id = commentID).comments[0].body.replace('&gt;', '> ')
        except Exception, e:
            print 'Failed to get submission/comment:'
            print e
            if retries > 0:
                retries -= 1
                self.lastPostTime = time.time()
                self.post_comment(submissionID, commentID, retries)
            else:
                print 'Retries exhausted. Abandoning.'
                return True
        self.hacky_sleep(5)
        print 'Logging in ...'
        try:
            self.r.login(self.username, self.password)
            self.hacky_sleep(5)
        except Exception, e:
            print 'Logging in failed. Retrying.'
            print e
            if retries > 0:
                retries -= 1
                self.lastPostTime = time.time()
                self.post_comment(submissionID, commentID, retries)
            else:
                print 'Retries exhausted. Abandoning.'
                return True
        print 'Posting comment ...'
        try:
            submission.add_comment(commentBody)
            return True
        except Exception, e:
            print 'Posting failed. You might be posting too often. Retrying.'
            print e
            if retries > 0:
                retries -= 1
                self.lastPostTime = time.time()
                self.post_comment(submissionID, commentID, retries)
            else:
                print 'Retries exhausted. Abandoning.'
                # Pretend it succeeded so that the entry gets removed.
                return True
        self.lastPostTime = time.time()


class SuggestionReader(object):
    
    def __init__(self, inputFile, ft):
        self.inputFile = inputFile
        self.ft        = ft
        self.lock      = lock
        self.commentsPosted = 0
    
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
    
    def load_suggestion_strings(self):
        with self.lock:
            with open(self.inputFile, 'r') as f:
                sugs = []
                for sug in f:
                    sugs.append(sug)
        return sugs
    
    def remove_suggestion_string(self, suggestion):
        with self.lock:
            with open(self.inputFile, 'r') as f:
                lines = f.readlines()
            with open(self.inputFile, 'w') as f:
                for line in lines:
                    if line.startswith(suggestion):
                        continue
                    else:
                        f.write(line)
        
    def loop(self):
        loadingChars = [u' \\ ',u' | ',u' / ',u' --']
        loadingIndex = 0
        os.system(['clear', 'cls'][os.name == 'nt'])
        while True:
            time.sleep(1)
            sys.stdout.write('\r')
            sys.stdout.flush()
            if os.stat(self.inputFile).st_size > 0:
                suggestions = self.load_suggestion_strings()
                for suggestion in suggestions:
                    args = [s.strip() for s in suggestion.split(";")]
                    if args[-1] == 'DEL':
                        if self.ft.delete_comment(args[0], 2):
                            self.remove_suggestion_string(suggestion)
                    elif args[-1] == 'ADD':
                        if self.ft.post_comment(args[0], args[1], 2):
                            self.commentsPosted += 1
                            self.remove_suggestion_string(suggestion)
            else:
                sys.stdout.write('%d comments posted.' % self.commentsPosted)
                sys.stdout.write(loadingChars[loadingIndex])
                if loadingIndex == 3:
                    loadingIndex = 0
                else:
                    loadingIndex += 1
                sys.stdout.flush()

    
def main():
    #if os.name != 'nt':
    #    print 'Proxy:'
    #    os.environ['http_proxy'] = raw_input()
    DATA     = os.path.abspath(os.path.join(os.path.curdir, 'suggestions'))
    COMPLETE = os.path.abspath(os.path.join(os.path.curdir, 'complete'))
    CREDENTIALS = os.path.abspath(os.path.join(os.path.curdir, 'credentials'))
    if os.path.exists(CREDENTIALS):
        with open(CREDENTIALS, 'r') as f:
            c = f.readlines()
        USER = c[0].strip()
        PASS = c[1].strip()
        DESCRIPTION = c[2].strip()
    else:
        print 'User:'
        USER = raw_input()
        print 'Password:'
        PASS = raw_input()
        print 'Description:'
        DESCRIPTION = raw_input()
    os.system(['clear', 'cls'][os.name == 'nt'])
    print DESCRIPTION
    ft = FrenchToste(3, USER, PASS, DESCRIPTION, DATA, COMPLETE)
    sr = SuggestionReader(DATA, ft)
    ft.find_suggestions(30, DATA)
    sr.loop()

if __name__ == '__main__':
    main()
