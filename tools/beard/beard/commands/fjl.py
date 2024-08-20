import re
import html


def do_fjl(html_log_file: str, label: str):
  line_rgx = re.compile(r'"timestamp"\><b>(?P<timestamp>\d\d:\d\d:\d\d).+?\[(?P<label>[\w\-]+)\](?P<msg>.*$)')
  tag_rgx = re.compile(r"<.*?>")
  with open(html_log_file) as html_log:
    for line in html_log:
      match = line_rgx.search(line)
      if not match:
        continue
      msg = html.unescape(tag_rgx.sub("", match.group("msg")))
      if not label:
        print(f"{match.group('timestamp')} [{match.group('label')}] {msg}")
      elif label == match.group("label"):
        print(f"{match.group('timestamp')}    {msg}")
