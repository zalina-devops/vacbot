function showToast(msg) {
  var t = document.querySelector('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(function() { t.classList.remove('show'); }, 3000);
}

// ========== Drag & Drop функционал ==========

let draggedCard = null;

function initDragAndDrop() {
  document.querySelectorAll('.kcard').forEach(card => {
    card.setAttribute('draggable', 'true');
  });
}

document.addEventListener('dragstart', function(e) {
  const card = e.target.closest('.kcard');
  if (!card) return;

  draggedCard = card;
  card.classList.add('dragging');
  e.dataTransfer.setData('text/plain', card.dataset.id);
  e.dataTransfer.effectAllowed = 'move';
});

document.addEventListener('dragend', function(e) {
  const card = e.target.closest('.kcard');
  if (card) {
    card.classList.remove('dragging');
  }
  document.querySelectorAll('.col-cards').forEach(col => {
    col.classList.remove('drag-over');
  });
  draggedCard = null;
});

document.querySelectorAll('.col-cards').forEach(column => {
  column.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    if (!column.classList.contains('drag-over')) {
      document.querySelectorAll('.col-cards').forEach(col => {
        col.classList.remove('drag-over');
      });
      column.classList.add('drag-over');
    }
  });

  column.addEventListener('dragleave', function(e) {
    if (column.classList.contains('drag-over')) {
      column.classList.remove('drag-over');
    }
  });

  column.addEventListener('drop', async function(e) {
    e.preventDefault();
    column.classList.remove('drag-over');

    if (!draggedCard) return;

    const cardId = draggedCard.dataset.id;
    const targetColumn = column.closest('.col');
    if (!targetColumn) return;

    const newStatus = targetColumn.dataset.status;

    const select = draggedCard.querySelector('.status-select');
    if (select) {
      select.value = newStatus;
    }

    await updateStatus(cardId, newStatus);

    column.appendChild(draggedCard);

    updateColumnCounters();

    showToast(`Перемещено в "${getColumnName(newStatus)}"`);
  });
});

function getColumnName(status) {
  const names = {
    'new': 'Новые',
    'starred': 'Избранное',
    'applied': 'Отклик отправлен',
    'interview': 'Собеседование',
    'rejected': 'Отказ',
    'offer': 'Оффер'
  };
  return names[status] || status;
}

async function updateStatus(id, newStatus) {
  try {
    const res = await fetch('/api/card/' + id + '/status', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: newStatus})
    });

    if (res.ok) {
      const data = await res.json();
      showToast('Статус обновлён');

      const card = document.querySelector(`.kcard[data-id="${id}"]`);
      if (card) {
        card.dataset.status = newStatus;

        const starBtn = card.querySelector('.star-btn');
        if (starBtn) {
          starBtn.textContent = data.starred ? '★' : '☆';
          starBtn.classList.toggle('active', data.starred);
        }

        card.classList.toggle('starred', data.starred);

        moveCardToColumn(card, newStatus);
      }

      updateFunnelStats();
    } else {
      showToast('Ошибка при обновлении статуса');
    }
  } catch (error) {
    console.error('Ошибка:', error);
    showToast('Ошибка соединения');
  }
}

function moveCardToColumn(card, newStatus) {
  const targetColumn = document.getElementById(`col-${newStatus}`);
  if (targetColumn) {
    card.remove();

    card.dataset.status = newStatus;

    const select = card.querySelector('.status-select');
    if (select) {
      select.value = newStatus;
    }

    targetColumn.appendChild(card);

    const emptyMsg = targetColumn.querySelector('.col-empty');
    if (emptyMsg) {
      emptyMsg.remove();
    }
  }

  updateColumnCounters();
}

function updateColumnCounters() {
  const columns = ['new', 'starred', 'applied', 'interview', 'rejected', 'offer'];
  columns.forEach(status => {
    const column = document.getElementById(`col-${status}`);
    if (column) {
      const count = column.children.length;
      const colHeader = column.closest('.col');
      const counterEl = colHeader?.querySelector('.col-cnt');
      if (counterEl) {
        counterEl.textContent = count;
      }
    }
  });
}

async function updateFunnelStats() {
  try {
    const res = await fetch('/api/stats');
    const stats = await res.json();

    const funnelSteps = document.querySelectorAll('.funnel-step');
    if (funnelSteps.length >= 6) {
      funnelSteps[0].querySelector('.fs-n').textContent = stats.total || 0;
      funnelSteps[1].querySelector('.fs-n').textContent = stats.board_stats?.starred || 0;
      funnelSteps[2].querySelector('.fs-n').textContent = stats.board_stats?.applied || 0;
      funnelSteps[3].querySelector('.fs-n').textContent = stats.board_stats?.interview || 0;
      funnelSteps[4].querySelector('.fs-n').textContent = stats.board_stats?.rejected || 0;
      funnelSteps[5].querySelector('.fs-n').textContent = stats.board_stats?.offer || 0;
    }
  } catch (error) {
    console.error('Ошибка обновления статистики:', error);
  }
}

async function toggleStar(id, btn) {
  const res = await fetch('/api/card/' + id + '/star', {method: 'POST'});
  if (res.ok) {
    const data = await res.json();
    btn.textContent = data.starred ? '★' : '☆';
    btn.classList.toggle('active', data.starred);
    const card = btn.closest('.kcard, .vcard');
    if (card) {
      card.classList.toggle('starred', data.starred);
    }

    if (!data.starred && card) {
      const parentCol = card.closest('.col');
      if (parentCol && parentCol.dataset.status === 'starred') {
        moveCardToColumn(card, 'new');
        const select = card.querySelector('.status-select');
        if (select) select.value = 'new';
        await updateStatus(id, 'new');
      }
    }

    updateFunnelStats();
    updateColumnCounters();
  }
}

async function runParser() {
    showLoadingModal('Запуск парсера', 'Идёт поиск вакансий. Пожалуйста, подождите...');

    try {
        const res = await fetch('/api/run-parser', { method: 'POST' });
        const data = await res.json();

        closeLoadingModal();

        if (data.ok) {
            showToast(`✅ ${data.message || 'Парсер завершён!'}`);
            setTimeout(() => {
                updateFunnelStats();
                location.reload();
            }, 1000);
        } else {
            showToast(`❌ Ошибка: ${data.error || 'неизвестная ошибка'}`, 'error');
        }
    } catch (err) {
        closeLoadingModal();
        showToast(`❌ Ошибка сети: ${err.message}`, 'error');
    }
}

var PROFILE = {
  name: 'Залина Алискерова',
  status: 'студентка 3 курса, специальность 09.02.07, Московский колледж (дистанционно)',
  skills: 'Python, HTML/CSS, Figma + графический планшет, Git, Docker, SQL (базовый), 1С (учебный)',
  projects: 'VacBot — парсер вакансий (Python, Flask, Docker, три источника данных); fullstack учебный проект',
  looking: 'удалённая стажировка или подработка, готова к обучению'
};

function getCardData(btn) {
  var actions = btn.closest('.vc-actions');
  return {
    id:      actions.dataset.id      || '',
    title:   actions.dataset.title   || '',
    company: actions.dataset.company || '',
    req:     actions.dataset.req     || ''
  };
}

function generateLetterFromCard(btn) {
  var d = getCardData(btn);
  generateLetter(d.id, d.title, d.company);
}

function adaptResumeFromCard(btn) {
  var d = getCardData(btn);
  adaptResume(d.id, d.title, d.company, d.req);
}

document.addEventListener('DOMContentLoaded', function() {
  initDragAndDrop();

  fetch('/api/stats')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var el = document.getElementById('last-update');
      if (el) el.textContent = data.total + ' вакансий';
    })
    .catch(function() {});
});

// ========== АДАПТАЦИЯ РЕЗЮМЕ ==========
async function adaptResume(vacancyId) {
    showLoadingModal('Адаптация резюме', '🤖 Искусственный интеллект анализирует вакансию и ваш профиль...');
    
    // Даём время на отрисовку модального окна
    await new Promise(resolve => setTimeout(resolve, 50));
    
    try {
        const res = await fetch(`/api/adapt-resume/${vacancyId}`, { method: 'POST' });
        const data = await res.json();
        closeLoadingModal();
        
        if (data.success) {
            showModal('Адаптированное резюме', data.text, vacancyId);
        } else {
            showToast('Ошибка: ' + (data.error || 'неизвестная'), 'error');
        }
    } catch (err) {
        closeLoadingModal();
        showToast('Ошибка сети: ' + err.message, 'error');
    }
}

// ========== ГЕНЕРАЦИЯ ПИСЬМА ==========
async function generateAICoverLetter(vacancyId) {
    showLoadingModal('Генерация письма', '✍️ ИИ составляет персонализированное сопроводительное письмо...');
    
    // Даём время на отрисовку модального окна
    await new Promise(resolve => setTimeout(resolve, 50));
    
    try {
        const res = await fetch(`/api/generate-cover-letter/${vacancyId}`, { method: 'POST' });
        const data = await res.json();
        closeLoadingModal();
        
        if (data.success) {
            showModal('Сопроводительное письмо', data.text);
        } else {
            showToast('Ошибка: ' + (data.error || 'неизвестная'), 'error');
        }
    } catch (err) {
        closeLoadingModal();
        showToast('Ошибка сети: ' + err.message, 'error');
    }
}

// ========== МОДАЛЬНОЕ ОКНО ДЛЯ РЕЗУЛЬТАТА ==========
function showModal(title, content, vacancyId = null) {
    const existing = document.getElementById('aiModal');
    if (existing) existing.remove();

    const isResume = title.includes('резюме');

    const modal = document.createElement('div');
    modal.id = 'aiModal';
    modal.className = 'ai-modal';
    modal.innerHTML = `
        <div class="ai-modal-overlay" onclick="document.getElementById('aiModal').remove()"></div>
        <div class="ai-modal-content">
            <div class="ai-modal-header">
                <h3>${title}</h3>
                <button class="close-modal" onclick="document.getElementById('aiModal').remove()">&times;</button>
            </div>
            <div class="ai-modal-body">${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
            <div class="ai-modal-footer">
                ${vacancyId && isResume ?
                    `<button class="nav-btn pdf-btn" onclick="window.open('/api/resume/pdf/${vacancyId}', '_blank')">Для себя (с метками)</button>
                     <button class="btn-emerald" onclick="window.open('/api/resume/pdf/${vacancyId}?clean=1', '_blank')">Для отправки (без меток)</button>` : ''}
                <button class="copy-btn nav-btn">Скопировать текст</button>
                <button class="close-btn nav-btn" onclick="document.getElementById('aiModal').remove()">Закрыть</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    modal.querySelector('.copy-btn').addEventListener('click', () => {
        navigator.clipboard.writeText(content);
        showToast('✅ Текст скопирован');
    });

    const escHandler = (e) => {
        if (e.key === 'Escape') {
            modal.remove();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// ========== УДАЛЕНИЕ ВАКАНСИИ ==========
async function deleteVacancy(vacancyId) {
    if (!confirm('Удалить эту вакансию? Данные не восстанавливаются.')) return;
    try {
        const res = await fetch(`/api/card/${vacancyId}/delete`, { method: 'DELETE' });
        const data = await res.json();
        if (data.ok) {
            showToast('Вакансия удалена');
            const card = document.querySelector(`.kcard[data-id="${vacancyId}"], .vcard[data-id="${vacancyId}"]`);
            if (card) card.remove();
            updateColumnCounters();
            updateFunnelStats();
        } else {
            showToast('Ошибка удаления', 'error');
        }
    } catch (err) {
        showToast('Ошибка сети', 'error');
    }
}

// ========== МОДАЛЬНОЕ ОКНО ЗАГРУЗКИ ==========
let loadingModalElement = null;

function showLoadingModal(title, message) {
    closeLoadingModal();
    
    const modal = document.createElement('div');
    modal.id = 'loadingModal';
    modal.className = 'loading-modal';
    modal.innerHTML = `
        <div class="loading-overlay"></div>
        <div class="loading-content">
            <div class="loading-header">
                <h3>${title}</h3>
            </div>
            <div class="loading-body">
                <div class="loading-animation">
                    <div class="loading-spinner"></div>
                    <div class="loading-progress">
                        <div class="loading-progress-bar"></div>
                    </div>
                </div>
                <p class="loading-message">${message}</p>
                <p class="loading-dots">⏳</p>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    loadingModalElement = modal;
    
    // Анимация точек
    let dotsFrame = 0;
    const dotsInterval = setInterval(() => {
        const dotsEl = document.querySelector('#loadingModal .loading-dots');
        if (dotsEl) {
            dotsFrame = (dotsFrame + 1) % 4;
            const dots = ['⏳', '⌛', '⏳', '⌛'];
            dotsEl.textContent = dots[dotsFrame];
        } else {
            clearInterval(dotsInterval);
        }
    }, 400);
    
    modal._dotsInterval = dotsInterval;
    
    // Показываем с анимацией
    setTimeout(() => {
        if (modal) modal.classList.add('show');
    }, 10);
}

function closeLoadingModal() {
    if (loadingModalElement) {
        const modal = loadingModalElement;
        const interval = modal._dotsInterval;
        if (interval) clearInterval(interval);
        modal.classList.remove('show');
        setTimeout(() => {
            if (modal && modal.parentNode) modal.remove();
        }, 300);
        loadingModalElement = null;
    }
}

function updateLoadingMessage(message) {
    const msgEl = document.querySelector('#loadingModal .loading-message');
    if (msgEl) msgEl.textContent = message;
}