
import wx
import time
import feedparser
from threading import Thread
from future import Future
import os.path
import webbrowser


class RssReader(Thread):
    def __init__(self, popupbox = None):

        Thread.__init__(self)

        self.rss_url_list = []
        self.entries = []
        self.interval = 10
        self.running = True
        self.last_update_date = ""
        self.popupbox = popupbox

        for line in open("data/rss_links.txt", "r").readlines():
            self.rss_url_list.append(line)
        self.start()

    def run(self):
        self._last = 0
        while self.running:
            now = time.time()
            if now > self._last + self.interval:
                self._last = now
                self.check()

            time.sleep(1)

    def items(self):
        if self.entries:
            if not self.popupbox.opened():
                yield self.entries[-1]
                del self.entries[-1]


    def check(self):
        calls = [Future(feedparser.parse, rss_url) for rss_url in self.rss_url_list]
        feeds = [future_obj() for future_obj in calls]

        for feed in feeds:
            item = feed['items'][0]
            if not os.path.exists("data/last_update.txt"): open("data/last_update.txt", "w")
            if not str(feed["url"]) in open("data/last_update.txt", "r").read():
                open("data/last_update.txt", "a").write(str(feed["url"] + " : " + str(item["date"])) + "\n")
            else:
                for line in open("data/last_update.txt", "r").readlines():
                    f = [l.strip() for l in line.split(" : ")]
                    if f[0] == str(feed["url"]):
                        if not f[1] == str(item["date"]):
                            item["date"].replace( str(item["date"]) , str(f[1]))
                            self.entries.append(item)

        if self.entries:
            for feed in feeds:
                open("data/last_update.txt", "w").write(str(feed["url"] + " : " + str(feed["items"][0]["date"])) + "\n")


    def close(self):
        self.running = False
        self.join()


class PopupBox(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, style=wx.NO_BORDER | wx.FRAME_NO_TASKBAR |wx.STAY_ON_TOP)

        self.screen = wx.GetClientDisplayRect()
        self.delay = 10
        self.popped = 0
        self.max_transparent = 200
        self.travel = 200
        self.trans = 0
        self.ease = 0.08
        self.padding = 12
        self.link = ""

        self.popup = self
        self.currentY = 0

        lines = 3
        lineHeight = wx.MemoryDC().GetTextExtent(" ")[1] -3

        self.popup.SetSize((250, (lineHeight * (lines + 1)) + (self.padding * 2)))

        self.box = self.popup.GetSize()
        self.currentX = (self.screen.width - self.box.width)

        self.panel = wx.Panel(self.popup, -1, size=self.popup.GetSize())

        # popup's click handler
        self.panel.Bind(wx.EVT_LEFT_DOWN, self.click)

        # popup's logo
        self.logo = wx.Bitmap("data/billeder/notifier_icon.png")
        wx.StaticBitmap(self.panel, -1, pos=(self.padding, self.padding)).SetBitmap(self.logo)

        self.Colors()

        self.timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.update_timer, self.timer)
        self.timer.Start()


    def Colors(self):
        self.panel.SetBackgroundColour('#404041') #242424

    def update_timer(self, event):
        if self.popped != 0 and self.popped + self.delay < time.time():
           self.hide()

    def show_box(self, text, link):
        self.link = link
        # create new text
        if hasattr(self, "text"):
            self.text.Destroy()
        popupSize = self.popup.GetSize()
        logoSize = self.logo.GetSize()

        self.text = wx.StaticText(self.panel, -1, text)

        self.text.SetForegroundColour(wx.WHITE)

        self.text.Bind(wx.EVT_LEFT_DOWN, self.click)
        self.text.Move((logoSize.width + (self.padding * 2), self.padding))
        self.text.SetSize((
            popupSize.width - logoSize.width - (self.padding * 3),
            popupSize.height - (self.padding * 2)
        ))

        self.popup.Show()

        self.animate(animate_in=True)
        self.popped = time.time()

    def click(self, event):
        """handles popup click"""
        if self.link:
            webbrowser.open_new_tab(self.link)
        self.hide()

    def hide(self):
        self.animate(animate_out=True)
        self.popup.Hide()
        self.popped = 0
        self.currentY = 0

    def opened(self):
        """returns true if popup is open"""

        return self.popped != 0

    def easy_to(self, pos, target, easy):
        pos += (target - pos) * easy
        return pos

    def animate(self, animate_in=False, animate_out=False):

        if animate_in:
            while self.trans != self.max_transparent:
                self.currentY = self.easy_to(self.currentY, self.travel, self.ease)
                disT = (self.travel - self.currentY)
                if disT > 1:
                    self.trans = (self.max_transparent/disT)
                else:
                    self.trans = self.max_transparent
                self.popup.Move((self.currentX, self.currentY))
                self.popup.SetTransparent(self.trans)
                self.popup.Update()
                self.popup.Refresh()
                time.sleep(float(1) / float(60))
        elif animate_out:

            while self.trans > 0:
                self.currentY = self.easy_to(self.currentY, self.travel * 2, self.ease)
                disT = ((self.travel * 2) - self.currentY)
                if disT > 1:
                    if (self.trans - (self.max_transparent / disT)) >= 0:
                        self.trans -= (self.max_transparent / disT)
                else:
                    self.trans = 0
                self.popup.Move((self.currentX, self.currentY))
                self.popup.SetTransparent(self.trans)
                self.popup.Update()
                self.popup.Refresh()
                time.sleep(float(1) / float(60))


class Taskbar(wx.TaskBarIcon):

    def __init__(self, menu):

        wx.TaskBarIcon.__init__(self)

        self.menu = menu

        # event handlers
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.click)
        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.click)
        self.Bind(wx.EVT_MENU, self.select)

        # icon state
        self.states = {
            "on": wx.Icon("data/billeder/reader_new.png", wx.BITMAP_TYPE_PNG),
            "off": wx.Icon("data/billeder/reader_empty.png", wx.BITMAP_TYPE_PNG)
        }
        self.setStatus("off")

    def click(self, event):

        menu = wx.Menu()
        for id, item in enumerate(self.menu):
            menu.Append(id, item[0])
        self.PopupMenu(menu)

    def setStatus(self, which):

        self.SetIcon(self.states[which])

    def select(self, event):

        self.menu[event.GetId()][1]()

    def close(self):

        self.Destroy()


# The main Application
class Notifier(wx.App):

    def __init__(self):

        wx.App.__init__(self, useBestVisual=True)


        # menu handlers
        menu = [
            ("Exit", self.exit),
        ]

        self.taskbar = Taskbar(menu)
        self.popup = PopupBox()
        self.reader = RssReader(self.popup)

        # main timer routine
        timer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.main, timer)
        timer.Start()
        self.MainLoop()

    def main(self, event):
            # show popup for next new item
            if self.reader.items():
                for item in self.reader.items():
                    self.popup.show_box(
                    "Update: %(title)s\n" % item, str(item["link"]))
                    status = "on"
                else:
                    status = "off"
                    # set icon status
                    self.taskbar.setStatus(status)

    def exit(self):

        # close objects and end
        self.taskbar.close()
        self.reader.close()
        self.Exit()


def main():
    Notifier()

if __name__ == '__main__':
    main()
