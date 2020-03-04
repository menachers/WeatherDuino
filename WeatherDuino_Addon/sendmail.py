#
# function to send a mail
#
from email.mime.text import MIMEText
import smtplib
def sendmail(usetls,smtppassword,smtpusername,smtpserver,sender,recipient,subject,content):

  # generate a RFC 2822 message
  msg = MIMEText(content)
  msg['From'] = sender
  msg['To'] = recipient
  msg['Subject'] = subject


  # start TLS encryption
  if usetls:
    # open SMTP connection
    server = smtplib.SMTP(smtpserver, 587)
    server.starttls()
  else:
    server = smtplib.SMTP(smtpserver)

  # login with specified account
  if smtpusername and smtppassword:
    server.login(smtpusername,smtppassword)

  # send generated message
  server.sendmail(sender,recipient,msg.as_string())

  # close SMTP connection
  server.quit()
