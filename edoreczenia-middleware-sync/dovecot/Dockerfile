FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Dovecot
RUN apt-get update && apt-get install -y \
    dovecot-core \
    dovecot-imapd \
    dovecot-lmtpd \
    && rm -rf /var/lib/apt/lists/*

# Create mail user
RUN useradd -m -s /bin/bash -u 1000 mailuser \
    && echo "mailuser:mailpass123" | chpasswd \
    && mkdir -p /home/mailuser/Maildir \
    && chown -R mailuser:mailuser /home/mailuser

# Create INBOX structure (required for Maildir)
RUN mkdir -p /home/mailuser/Maildir/cur \
    && mkdir -p /home/mailuser/Maildir/new \
    && mkdir -p /home/mailuser/Maildir/tmp

# Create e-Doreczenia folders (INBOX.e-Doreczenia = .INBOX.e-Doreczenia in Maildir)
RUN mkdir -p /home/mailuser/Maildir/.INBOX.e-Doreczenia/cur \
    && mkdir -p /home/mailuser/Maildir/.INBOX.e-Doreczenia/new \
    && mkdir -p /home/mailuser/Maildir/.INBOX.e-Doreczenia/tmp \
    && mkdir -p /home/mailuser/Maildir/.e-Doreczenia-Wyslij/cur \
    && mkdir -p /home/mailuser/Maildir/.e-Doreczenia-Wyslij/new \
    && mkdir -p /home/mailuser/Maildir/.e-Doreczenia-Wyslij/tmp \
    && mkdir -p /home/mailuser/Maildir/.Sent.e-Doreczenia/cur \
    && mkdir -p /home/mailuser/Maildir/.Sent.e-Doreczenia/new \
    && mkdir -p /home/mailuser/Maildir/.Sent.e-Doreczenia/tmp \
    && chown -R mailuser:mailuser /home/mailuser/Maildir

# Configure Dovecot
RUN echo 'protocols = imap lmtp' > /etc/dovecot/dovecot.conf \
    && echo 'listen = *' >> /etc/dovecot/dovecot.conf \
    && echo 'mail_location = maildir:~/Maildir' >> /etc/dovecot/dovecot.conf \
    && echo 'auth_mechanisms = plain login' >> /etc/dovecot/dovecot.conf \
    && echo 'disable_plaintext_auth = no' >> /etc/dovecot/dovecot.conf \
    && echo 'ssl = no' >> /etc/dovecot/dovecot.conf \
    && echo 'passdb {' >> /etc/dovecot/dovecot.conf \
    && echo '  driver = pam' >> /etc/dovecot/dovecot.conf \
    && echo '}' >> /etc/dovecot/dovecot.conf \
    && echo 'userdb {' >> /etc/dovecot/dovecot.conf \
    && echo '  driver = passwd' >> /etc/dovecot/dovecot.conf \
    && echo '}' >> /etc/dovecot/dovecot.conf \
    && echo 'service imap-login {' >> /etc/dovecot/dovecot.conf \
    && echo '  inet_listener imap {' >> /etc/dovecot/dovecot.conf \
    && echo '    port = 143' >> /etc/dovecot/dovecot.conf \
    && echo '  }' >> /etc/dovecot/dovecot.conf \
    && echo '}' >> /etc/dovecot/dovecot.conf \
    && echo 'namespace inbox {' >> /etc/dovecot/dovecot.conf \
    && echo '  inbox = yes' >> /etc/dovecot/dovecot.conf \
    && echo '  separator = .' >> /etc/dovecot/dovecot.conf \
    && echo '}' >> /etc/dovecot/dovecot.conf \
    && echo 'log_path = /var/log/dovecot.log' >> /etc/dovecot/dovecot.conf

# Install netcat for healthcheck
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Create log file
RUN touch /var/log/dovecot.log && chmod 666 /var/log/dovecot.log

# Expose IMAP port
EXPOSE 143

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD nc -z localhost 143 || exit 1

# Run Dovecot in foreground
CMD ["dovecot", "-F"]
