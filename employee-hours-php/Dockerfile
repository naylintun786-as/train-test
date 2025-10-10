# Simple Apache + PHP image with mysqli enabled
FROM php:8.2-apache

# Install mysqli and required extensions
RUN docker-php-ext-install mysqli && docker-php-ext-enable mysqli

# Enable Apache modules commonly needed
RUN a2enmod rewrite

# Copy source code
COPY . /var/www/html/

# Set working directory
WORKDIR /var/www/html

# Permissions (safe defaults for dev)
RUN chown -R www-data:www-data /var/www/html

# Expose port (apache default)
EXPOSE 80
