"""One delivery batch for platforms that schedule jobs instead of a VM worker."""
import index as app
import mail_delivery

if __name__=='__main__':
    app.cipher()
    print(mail_delivery.deliver(app, maximum=20))
