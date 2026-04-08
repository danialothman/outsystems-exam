# Deployment Guide - OutSystems ODC Exam Simulator

## Quick Start (2 minutes)

### Linux/macOS
```bash
cd outsystems-exam
chmod +x run.sh
./run.sh
```

### Windows
```cmd
cd outsystems-exam
pip install -r requirements.txt
python app.py
```

Then visit: `http://localhost:5000`

---

## Detailed Setup

### System Requirements
- Python 3.7 or higher
- pip (comes with Python)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 100MB free disk space
- Internet connection not required (fully offline capable)

### Installation Steps

1. **Verify Python Installation**
   ```bash
   python --version  # Should show 3.7+
   pip --version     # Should show 20+
   ```

2. **Create Virtual Environment (Recommended)**
   ```bash
   python -m venv venv
   
   # Activate venv
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

5. **Access the Exam**
   - Open browser to `http://localhost:5000`
   - The exam loads automatically
   - Timer starts at 120:00

---

## Configuration

### Change Port
If port 5000 is already in use:

**app.py** (last line):
```python
if __name__ == '__main__':
    app.run(debug=True, port=8080)  # Change 5000 to 8080
```

### Disable Debug Mode (Production)
**app.py** (last line):
```python
if __name__ == '__main__':
    app.run(debug=False)  # Set to False for production
```

### Change Exam Duration
**app.py** (line with `7200`):
```python
3600    # 60 minutes
7200    # 120 minutes (default)
14400   # 240 minutes
```

### Adjust Passing Score
**app.py** (in `submit_exam()` function):
```python
passed = percentage >= 70  # Change 70 to desired percentage
```

---

## Advanced Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t outsystems-exam .
docker run -p 5000:5000 outsystems-exam
```

### Gunicorn (Production WSGI Server)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Nginx Reverse Proxy

```nginx
upstream flask_app {
    server localhost:5000;
}

server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd Service (Linux)

Create `/etc/systemd/system/outsystems-exam.service`:
```ini
[Unit]
Description=OutSystems Exam Simulator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/www-data/outsystems-exam
ExecStart=/usr/bin/python3 /home/www-data/outsystems-exam/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable outsystems-exam
sudo systemctl start outsystems-exam
```

---

## Troubleshooting

### Issue: "Port 5000 already in use"
**Solution**: Use different port (see Configuration section above)

```bash
# Find process using port 5000
lsof -i :5000  # Linux/macOS
netstat -ano | findstr :5000  # Windows

# Kill process (macOS/Linux)
kill -9 <PID>
```

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Install Flask
```bash
pip install flask
# Or
pip install -r requirements.txt
```

### Issue: Questions not loading
1. Check Flask is running without errors
2. Open browser console (F12 → Console tab)
3. Refresh page (Ctrl+R or Cmd+R)
4. Check server output for errors

### Issue: Timer not working
1. Timer syncs with server on page load
2. If incorrect, refresh the page
3. Check browser time is correct

### Issue: Answers not saving
1. Check network tab in browser (F12 → Network)
2. Look for failed `/api/save-answer` requests
3. Verify server is running
4. Try different question

### Issue: "Secret key is the same"
This is normal in development. For production:

**app.py** (line 10):
```python
app.secret_key = 'your-random-secret-key-here'
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Security Considerations

### For Production Deployment

1. **Change Secret Key** (See above)
2. **Disable Debug Mode**
   ```python
   app.run(debug=False)
   ```

3. **Use HTTPS**
   - Set up SSL/TLS certificate
   - Redirect HTTP to HTTPS
   - Use secure cookies

4. **Add Authentication** (if sharing)
   ```python
   # Add basic authentication to protect exam
   from flask_httpauth import HTTPBasicAuth
   auth = HTTPBasicAuth()
   ```

5. **Rate Limiting**
   ```bash
   pip install Flask-Limiter
   ```

6. **Run Behind Reverse Proxy**
   - Use Nginx or Apache
   - Firewall non-admin ports
   - Enable logging

7. **Regular Backups**
   - Keep source code backed up
   - Document any customizations

---

## Monitoring

### Enable Logging
**app.py** (after imports):
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Access Logs
With Gunicorn:
```bash
gunicorn \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  app:app
```

### Performance Monitoring
```bash
pip install flask-cors flask-caching
```

---

## Scaling

### Multiple Instances
Use load balancer (Nginx, HAProxy) to distribute traffic:
```bash
# Instance 1
python app.py --port 5000

# Instance 2
python app.py --port 5001

# Instance 3
python app.py --port 5002
```

### Session Persistence
Current implementation uses Flask sessions (in-memory). For load balancing:

```python
from flask_session import Session
import redis

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379')
Session(app)
```

---

## Maintenance

### Update Questions
1. Edit `app.py`
2. Modify `EXAM_QUESTIONS` list
3. Restart Flask server
4. Users with active sessions will keep their old questions
5. New sessions will have updated questions

### Backup Exam Data
Questions are hardcoded in `app.py`. To backup:
```bash
cp app.py app.py.backup.$(date +%s)
```

### Monitor Performance
- Check response times in browser network tab
- Monitor server CPU/memory usage
- Enable Flask debug toolbar for development

---

## Testing the Installation

### Verify All Components
```bash
# 1. Check Python
python --version

# 2. Check Flask installation
python -c "import flask; print(flask.__version__)"

# 3. Start server
python app.py

# 4. In another terminal, test endpoint
curl http://localhost:5000/

# 5. Test API
curl http://localhost:5000/api/questions
```

### Manual Exam Test
1. Open `http://localhost:5000`
2. Click through a few questions
3. Try flagging a question
4. Check timer updates
5. Answer some questions
6. Submit exam
7. Verify results display correctly

---

## Rollback Procedure

If something goes wrong:

```bash
# Stop the server (Ctrl+C if running in terminal)

# Restore from backup
cp app.py.backup.[timestamp] app.py

# Restart
python app.py
```

---

## Support

### Common Questions

**Q: Can I run this offline?**
A: Yes, fully offline. Just need Python and modern browser.

**Q: Can I share this with students?**
A: Yes, put it on a shared server or give them the installation files.

**Q: Can I modify questions?**
A: Yes, edit `app.py` and modify `EXAM_QUESTIONS` list.

**Q: Will exam progress save if I close browser?**
A: No, session is lost. Exams must be completed in one sitting.

**Q: Can I add a database?**
A: Yes, but not necessary. Session-based system works fine for single-user or small groups.

---

## Next Steps

1. Install and run the application
2. Take a practice exam to test functionality
3. Share with colleagues
4. Customize questions if needed
5. Deploy to shared server for broader access

For additional help, check the README.md file or review the Flask documentation at flask.palletsprojects.com
