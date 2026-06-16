# Images and Assets

This directory contains all static images and assets for the application.

## Structure

- `logo-default.svg` - Default system logo (can be overridden in system settings)
- `favicon.svg` - Browser favicon
- `placeholder-company.svg` - Placeholder for company logos
- `login-bg-default.svg` - Default login background
- `icons/` - SVG icons used throughout the application

## Customization

### System Logo
Upload a custom logo via the System Settings page (Super Admin only).
Recommended size: 150x50px

### Company Logos
Each company can upload their own logo via Company Settings.
Recommended size: 200x200px
Supported formats: PNG, JPG, SVG

### Login Background
Upload a custom background via System Settings.
Recommended size: 1920x1080px or larger

## Notes

- All default images are SVG for scalability
- Images are stored in the database via Django's ImageField
- Uploaded images are stored in the `media/` directory
