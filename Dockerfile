FROM mitmproxy/mitmproxy:latest

# Copy Scripts
COPY Scripts/ /home/mitmproxy/scripts/

# Create Data directory for volume mount
RUN mkdir -p /home/mitmproxy/Data

# Copy Entrypoint
COPY entrypoint.sh /home/mitmproxy/entrypoint.sh
RUN chmod +x /home/mitmproxy/entrypoint.sh

# Expose ports
EXPOSE 8080 8081

# Set the entrypoint
ENTRYPOINT ["/home/mitmproxy/entrypoint.sh"]
