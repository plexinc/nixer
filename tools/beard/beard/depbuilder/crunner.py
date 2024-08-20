""" Copied from conan - a runner class that abstracts subprocess """

#pylint: disable=too-many-branches, too-few-public-methods

from subprocess import Popen, run, PIPE, STDOUT

class OutputBuffer(object):
  """ just a buffer to store information from a command run """
  lines = []

  def write(self, line):
    """ write """
    self.lines.append(line.rstrip())

  def clear(self):
    """ clear the buffer """
    self.lines = []

  def __str__(self):
    return "\n".join(self.lines)

def decode_text(text):
  """ method to convert charsets """
  decoders = ["utf-8", "Windows-1252"]
  for decoder in decoders:
    try:
      return text.decode(decoder)
    except UnicodeDecodeError:
      continue
  return text.decode("utf-8", "ignore")  # Ignore not compatible characters

class CRunner(object):
  """ the main runner class """
  def __call__(self, command, output, cwd=None):
    """ There are two options, with or without you (sorry, U2 pun :)
    With or without output. Probably the Popen approach would be fine for both cases
    but I found it more error prone, slower, problems with very large outputs (typical
    when building C/C++ projects...) so I prefer to keep the os.system one for
    most cases, in which the user does not want to capture the output, and the Popen
    for cases they want
    """
    if output is True:
      try:
        proc = run(command, shell=True, cwd=cwd)
        return proc.returncode
      except Exception as exc:
        raise Exception("Error while executing '%s'\n\t%s" % (command, str(exc)))
    else:
      proc = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT, cwd=cwd)
      if hasattr(output, "write"):
        while True:
          line = proc.stdout.readline()
          if not line:
            break
          output.write(decode_text(line))
      out, err = proc.communicate()

      if hasattr(output, "write"):
        if out:
          output.write(decode_text(out))
        if err:
          output.write(decode_text(err))

      return proc.returncode
