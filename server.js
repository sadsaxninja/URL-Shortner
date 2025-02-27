const express = require('express');
const mongoose = require('mongoose');
const nanoid = require('nanoid');

const app = express();
app.use(express.static('public'));
app.use(express.json());

// Connect to MongoDB
mongoose.connect('mongodb://localhost/url-shortener', { useNewUrlParser: true, useUnifiedTopology: true });

// Define URL schema
const urlSchema = new mongoose.Schema({
    originalUrl: String,
    shortId: String
});

const Url = mongoose.model('Url', urlSchema);

// Shorten URL endpoint
app.post('/shorten', async (req, res) => {
    const { url } = req.body;
    const shortId = nanoid.nanoid(6);

    try {
        const urlDocument = new Url({ originalUrl: url, shortId });
        await urlDocument.save();
        res.json({ shortUrl: `http://localhost:3000/${shortId}` });
    } catch (error) {
        res.status(500).json({ error: 'Error shortening URL' });
    }
});

// Redirect to original URL
app.get('/:shortId', async (req, res) => {
    const { shortId } = req.params;

    try {
        const urlDocument = await Url.findOne({ shortId });
        if (urlDocument) {
            res.redirect(urlDocument.originalUrl);
        } else {
            res.status(404).send('URL not found');
        }
    } catch (error) {
        res.status(500).send('Server error');
    }
});

// Start the server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});