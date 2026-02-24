export const parseUrl = (url, params) => {
  Object.keys(params).forEach((key) => {
    url = url.replace(`:${key}`, params[key]);
  });
  return url;
};

export const title = (text) => {
  if (!text) return '';
  let items = text.split(' ');
  items = items.map((item) => item.charAt(0).toUpperCase() + item.slice(1));
  items = items.join(' ');
  items = text.split('-');
  items = items.map((item) => item.charAt(0).toUpperCase() + item.slice(1));
  items = items.join('-');
  return items;
};

export const filterCount = (filters) => {
  if (!filters) filters = {};
  let count = 0;
  if (filters.restaurant) count += 1;
  if (filters.company) count += 1;
  if (filters.date_range) count += 1;
  if (filters.vendor) count += 1;

  return count;
};

export const toCurrency = (value) => {
  if (!value) value = 0.0;
  value = +value;
  const isNegative = value < 0;
  if (isNegative) value *= -1;
  const formattedString = `${value.toFixed(2).replace(/(\d)(?=(\d\d\d)+(?!\d))/g, '$1,')}`;
  if (isNegative) return `-$ ${formattedString}`;
  return `$ ${formattedString}`;
};

export const toCurrencyNoSpace = (value) => {
  if (!value) value = 0.0;
  value = +value;
  const isNegative = value < 0;
  if (isNegative) value *= -1;
  const formattedString = `${value.toFixed(2).replace(/(\d)(?=(\d\d\d)+(?!\d))/g, '$1,')}`;
  if (isNegative) return `-$${formattedString}`;
  return `$${formattedString}`;
};

export const round = (value) => {
  if (!value) value = 0.0;
  value = +value;
  return value.toFixed(2);
};

export const roundTo = (value, to) => {
  if (!value) value = 0.0;
  value = +value;
  return value.toFixed(to);
};

export const replaceAll = (string, stringToFind, stringToReplace) => {
  if (stringToFind === stringToReplace) return this;
  let temp = string;
  let index = temp.indexOf(stringToFind);
  while (index !== -1) {
    temp = temp.replace(stringToFind, stringToReplace);
    index = temp.indexOf(stringToFind);
  }
  return temp;
};

export const strToBool = (value) => {
  if (!value) return false;
  value = value.toLowerCase();
  return value === 'true';
};

export const encodeUrl = (url, params) => {
  if (!params) return url;
  let paramsString = '';
  Object.keys(params).forEach((key) => {
    paramsString = `${paramsString + key}=${encodeURIComponent(params[key])}&`;
  });
  paramsString = paramsString.substring(0, paramsString.length - 1);
  return `${url}?${paramsString}`;
};

export const getQueryParams = (url) => {
  const regex = /[?&]([^=#]+)=([^&#]*)/g;
  const params = {};
  let match;
  // eslint-disable-next-line no-cond-assign
  while (match = regex.exec(url)) {
    // eslint-disable-next-line prefer-destructuring
    params[match[1]] = match[2];
  }
  return params;
};
