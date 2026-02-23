import moment from 'moment';

export const parserInvoiceDate = (date = null) => {
  if (!date) {
    return '';
  }
  return moment(date).format('MMM DD, YYYY');
};

export const parserInvoiceTime = (date = null) => {
  if (!date) {
    return '';
  }
  return moment(date).format('hh:mm A');
};

export const formatDateRange = (dates) => {
  const { start, end } = dates;
  if (!start || !end) return '';
  return `${moment(start).format('MM/DD/YY')} - ${moment(end).format('MM/DD/YY')}`;
};

export const formatTakenAt = (date) => {
  if (!date) return '';
  return moment(date).format('MM/DD/YY hh:mm A');
};

export const formatCalendarDate = () => moment().format('YYYY-MM-DD');

export const getDateRange = (type) => {
  let start = null;
  let end = null;

  if (type === 'today') {
    start = moment();
    end = moment();
  } else if (type === 'yesterday') {
    start = moment().subtract(2, 'days');
    end = moment().subtract(1, 'days');
  } else if (type === 'last_7_days') {
    start = moment().subtract(7, 'days');
    end = moment();
  } else if (type === 'this_month') {
    start = moment().startOf('month');
    end = moment();
  } else if (type === 'last_30_days') {
    start = moment().subtract(1, 'month');
    end = moment();
  } else if (type === 'last_3_months') {
    start = moment().subtract(3, 'month');
    end = moment();
  } else if (type === 'last_1_year') {
    start = moment().subtract(1, 'year');
    end = moment();
  }
  if (start && end) {
    start = start.format('YYYY-MM-DD');
    end = end.format('YYYY-MM-DD');
    return {
      start, end
    };
  }
  return null;
};

export const formatDate = (date, format) => {
  if (!date) {
    return '';
  }
  if (!format) {
    format = 'YYYY-MM-DD';
  }
  return moment(date).format(format);
};

export const parseTransactionDate = (date = null) => {
  if (!date) {
    return '';
  }
  return moment(date).format('MMM DD, YYYY');
};

export const formatReceiptTakenAt = (date) => {
  if (!date) return '';
  return moment(date).format('MM/DD/YYYY');
};
