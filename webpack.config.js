const path = require('path')
const isDevelopment = process.env.NODE_ENV !== 'production'

module.exports = {
  mode: isDevelopment? 'development': 'production',
  entry: './application/web/frontend/index.js',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'application/web/static'),
    publicPath: '/static/'
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /(node_modules|bower_components)/,
        use: {
          loader: 'babel-loader',
          options: { presets: ['es2015', 'react'] }
        }
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      }
    ]
  }
}
