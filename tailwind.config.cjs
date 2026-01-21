/**
 * Minimal Tailwind config so Tailwind CSS IntelliSense can locate
 * classes used in the Flask/Jinja templates.
 */
module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/**/*.py',
    './*.py',
    './tests/**/*.py',
    './utility/**/*.py'
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
