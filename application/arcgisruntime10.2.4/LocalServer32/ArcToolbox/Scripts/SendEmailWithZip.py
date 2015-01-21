import arcgisscripting, smtplib, os, sys, traceback

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

gp = arcgisscripting.create(9.3)

#**********************************************************************
# Description:
#   Emails a file. File is assumed to be a zip file. Routine either attaches
#   the zip file to the email or sends the URL to the zip file.
#
# Parameters:
#   1 - File to send.
#   2 - Email address to send file.
#   3 - Name of outgoing email server.
#   4 - Output boolean success flag.
#**********************************************************************

def send_mail(send_from, send_to, subject, text, f, server, smtpUser="", smtpPwd=""):
    try:
        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = COMMASPACE.join(send_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach( MIMEText(text) )
        part = MIMEBase('application', "zip")   # Change if different file type sent.
        part.set_payload( open(f,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)
            
        smtp = smtplib.SMTP(server)
        
        # If your server requires user/password
        if smtpUser != "" and smtpPwd != "":
            smtp.login(smtpUser, smtpPwd)
        
        smtp.sendmail(send_from, send_to, msg.as_string())
        smtp.close()
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
        raise Exception("SendEmailError:" + pymsg)

   
if __name__ == '__main__':

    sendto = gp.GetParameterAsText(0).split(";")
    fromaddr = gp.GetParameterAsText(1)
    subject = gp.GetParameterAsText(2)
    text = gp.GetParameterAsText(3)
    zipfile = gp.GetParameterAsText(4).replace("\\",os.sep)
    maxsize = int(gp.GetParameterAsText(5)) * 1000000
    smtpMailServer = gp.GetParameterAsText(6)
    smtpUser = gp.GetParameterAsText(7)
    smtpPwd = gp.GetParameterAsText(8)
    
    try: 
        zipsize = os.path.getsize(zipfile)
        #Message"Zip file size = "
        gp.AddMessage(gp.GetIDMessage(86156) + str(zipsize))
        if  zipsize <= maxsize:
            send_mail(fromaddr, sendto, subject, text, zipfile, smtpMailServer, smtpUser, smtpPwd)
            #Message "Sent zipfile to %s from %s"
            gp.AddIDMessage("INFORMATIVE", 86154, sendto, fromaddr)
            gp.SetParameterAsText(9, "True")
        else:
            #Message "The resulting zip file is too large (%sMB).  Must be less than %MB.  Please
            # digitize a smaller Area of Interest."
            gp.AddIDMessage("ERROR", 86155, str(round(zipsize / 1000000.0, 2)),
                            str(round(maxsize / 1000000.0, 2)))
            gp.SetParameterAsText(9, "False")
            raise Exception

    except:
        # Return any python specific errors as well as any errors from the geoprocessor
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n    " + \
                str(sys.exc_type)+ ": " + str(sys.exc_value) + "\n"
        gp.AddError(pymsg)
        #Message "Unable to send email"
		#gp.AddIDMessage("ERROR", 86157)
        gp.AddError("ERROR, Unable to send email")