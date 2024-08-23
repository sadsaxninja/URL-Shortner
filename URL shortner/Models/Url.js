const mongoose = require('mongoose');
const shortid = require('shortid');

const UrlSchema = new mongoose.Schema({
    originalUrl: { type: String, required: true },
    shortUrl: { type: String, required: true, default: shortid.generate },
    date: { type: String, default: Date.now },
});

module.exports = mongoose.model('Url', UrlSchema);
