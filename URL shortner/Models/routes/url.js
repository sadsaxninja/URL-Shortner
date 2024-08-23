const express = require('express');
const validUrl = require('valid-url');
const shortid = require('shortid');
const Url = require('../models/Url');

const router = express.Router();

// @route   POST /api/url/shorten
// @desc    Create short URL
router.post('/shorten', async (req, res) => {
    const { originalUrl } = req.body;
    const base = process.env.BASE_URL;

    if (!validUrl.isUri(base)) {
        return res.status(401).json('Invalid base URL');
    }

    const urlCode = shortid.generate();

    if (validUrl.isUri(originalUrl)) {
        try {
            let url = await Url.findOne({ originalUrl });

            if (url) {
                res.json(url);
            } else {
                const shortUrl = `${base}/${urlCode}`;

                url = new Url({
                    originalUrl,
                    shortUrl,
                    urlCode,
                    date: new Date(),
                });

                await url.save();

                res.json(url);
            }
        } catch (err) {
            console.error(err);
            res.status(500).json('Server error');
        }
    } else {
        res.status(401).json('Invalid original URL');
    }
});

// @route   GET /:code
// @desc    Redirect to original URL
router.get('/:code', async (req, res) => {
    try {
        const url = await Url.findOne({ urlCode: req.params.code });

        if (url) {
            return res.redirect(url.originalUrl);
        } else {
            return res.status(404).json('No URL found');
        }
    } catch (err) {
        console.error(err);
        res.status(500).json('Server error');
    }
});

module.exports = router;
