require('dotenv').config();
const axios = require('axios');

console.log('Testing Brevo API key...');
console.log('EMAIL_USER:', process.env.EMAIL_USER);
console.log('BREVO_API_KEY Prefix:', process.env.BREVO_API_KEY ? process.env.BREVO_API_KEY.slice(0, 20) + '...' : 'MISSING');

axios.post('https://api.brevo.com/v3/smtp/email', {
    sender: { name: 'Finance AI', email: process.env.EMAIL_USER || 'noreply@financeai.com' },
    to: [{ email: process.env.EMAIL_USER || 'tarunpuniya287@gmail.com' }],
    subject: 'Test OTP Email',
    htmlContent: '<p>Test email</p>'
}, {
    headers: {
        'api-key': (process.env.BREVO_API_KEY || '').trim(),
        'Content-Type': 'application/json'
    }
}).then(r => {
    console.log('✅ SUCCESS Response:', r.status, r.data);
}).catch(e => {
    console.error('❌ ERROR Response Status:', e.response ? e.response.status : 'No Status');
    console.error('❌ ERROR Response Data:', e.response ? e.response.data : e.message);
});
