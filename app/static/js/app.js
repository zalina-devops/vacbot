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
        // Обновляем атрибут data-status
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

// Адаптация резюме
async function adaptResume(vacancyId) {
    showToast('Адаптирую резюме...');
    try {
        const res = await fetch(`/api/adapt-resume/${vacancyId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showModal('Адаптированное резюме', data.text);
        } else {
            showToast('Ошибка: ' + (data.error || 'неизвестная'), 'error');
        }
    } catch (err) {
        showToast('Ошибка сети', 'error');
    }
}

// Генерация письма через AI
async function generateAICoverLetter(vacancyId) {
    showToast('Генерирую письмо...');
    try {
        const res = await fetch(`/api/generate-cover-letter/${vacancyId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showModal('Сопроводительное письмо', data.text);
        } else {
            showToast('Ошибка: ' + (data.error || 'неизвестная'), 'error');
        }
    } catch (err) {
        showToast('Ошибка сети', 'error');
    }
}

function showModal(title, content) {
    const existing = document.getElementById('aiModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'aiModal';
    modal.innerHTML = `
        <div class="ai-modal-header">
            <h3>${title}</h3>
            <button class="close-modal">&times;</button>
        </div>
        <div class="ai-modal-body">${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
        <div class="ai-modal-footer">
            <button class="copy-btn nav-btn">Скопировать текст</button>
            <button class="close-btn nav-btn">Закрыть</button>
        </div>
    `;
    document.body.appendChild(modal);

    const closeFn = () => modal.remove();
    modal.querySelector('.close-modal').addEventListener('click', closeFn);
    modal.querySelector('.close-btn').addEventListener('click', closeFn);
    modal.querySelector('.copy-btn').addEventListener('click', () => {
        navigator.clipboard.writeText(content);
        showToast('Текст скопирован');
    });
}

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

let loadingInterval = null;
let loadingFrame = 0;

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

    loadingFrame = 0;
    if (loadingInterval) clearInterval(loadingInterval);
    loadingInterval = setInterval(() => {
        const dotsEl = document.querySelector('#loadingModal .loading-dots');
        if (dotsEl) {
            loadingFrame = (loadingFrame + 1) % 4;
            const dots = ['⏳', '⌛', '⏳', '⌛'];
            dotsEl.textContent = dots[loadingFrame];
        } else {
            clearInterval(loadingInterval);
        }
    }, 400);

    setTimeout(() => {
        const modalEl = document.getElementById('loadingModal');
        if (modalEl) modalEl.classList.add('show');
    }, 10);
}

function closeLoadingModal() {
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
    const modal = document.getElementById('loadingModal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

function updateLoadingMessage(message) {
    const msgEl = document.querySelector('#loadingModal .loading-message');
    if (msgEl) msgEl.textContent = message;
}
