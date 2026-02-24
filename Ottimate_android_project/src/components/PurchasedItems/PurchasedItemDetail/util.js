import Colors from '../../../styles/Colors';
import { formatDate } from '../../../utils/DateFormatter';
import { title } from '../../../utils/StringFormatter';

// eslint-disable-next-line import/prefer-default-export
export const generateChartData = (trend, key, restaurantNameJson) => {
  trend.sort((a, b) => {
    if (a.date < b.date) return -1;
    if (a.date > b.date) return 1;
    if (a.date < b.date) return -1;
    if (a.date > b.date) return 1;
    return 0;
  });

  const colors = [Colors.primary, Colors.green, Colors.red, Colors.gray, Colors.deepSkyBlue, Colors.warning, Colors.canceled];
  const restaurantJson = {};
  const restaurantDateJson = {};
  let labels = [];
  const datasets = [];
  const legend = [];

  trend.forEach((item) => {
    if (labels.indexOf(item.date) === -1) labels.push(item.date);
    let restaurants = restaurantJson[item.restaurant];
    if (!restaurants) restaurants = [];
    restaurants.push(item);
    restaurantJson[item.restaurant] = restaurants;
  });

  Object.keys(restaurantJson).forEach((restaurantId) => {
    const dateJson = {};
    restaurantJson[restaurantId].forEach((item) => {
      dateJson[item.date] = item;
    });
    restaurantDateJson[restaurantId] = dateJson;
  });

  Object.keys(restaurantJson).forEach((restaurantId, index) => {
    const data = [];
    const wholeData = [];
    let lastValue = null;

    labels.forEach((label) => {
      const item = restaurantDateJson[restaurantId][label];
      let value = null;
      if (item) value = item[key];
      if (value) {
        lastValue = value;
      } else {
        value = lastValue;
      }
      data.push(value);
      wholeData.push(item);
    });
    let color = colors[index];
    if (!color) color = Colors.deepSkyBlue;
    datasets.push({
      color: () => color,
      labelColor: () => color,
      propsForDots: {
        r: '3',
        strokeWidth: '1',
        stroke: color
      },
      data,
      wholeData
    });
  });

  Object.keys(restaurantJson).forEach((restaurantId) => {
    legend.push(restaurantNameJson[restaurantId]);
  });

  const MAX_LABLES = 5;
  const takenIndex = Math.floor(labels.length / MAX_LABLES);
  labels = labels.map((item, index) => {
    let value = formatDate(item, 'DD MMM');
    if (index % takenIndex !== 0 && labels.length > MAX_LABLES) value = '';
    return value;
  });

  return {
    labels,
    datasets,
    legend
  };
};

export const generateHighChartData = (trend, key, restaurantNameJson) => {
  const restaurantJson = {};
  const Highcharts = 'Highcharts';

  const chartConfig = {
    colors: [Colors.primary, Colors.green, Colors.red, Colors.gray, Colors.fadedBlue, Colors.deepSkyBlue, Colors.primaryLight],
    title: {
      text: ' '
    },
    xAxis: {
      type: 'datetime',
      tickPixelInterval: 150,
      dateTimeLabelFormats: {
        day: '%d %m',
      },
    },
    yAxis: {
      title: {
        text: title(key)
      },
      min: 0
    },
    tooltip: {
      enabled: false
    },
    credits: {
      enabled: false
    },
    exporting: {
      enabled: false
    },
    legend: {
      enabled: true
    },
    animation: Highcharts.svg
  };

  trend.forEach((item) => {
    let series = restaurantJson[item.restaurant];
    if (!series) {
      series = [];
    }
    series.push({
      x: Date.parse(item.date),
      y: item[key],
      customValue: JSON.stringify(item)
    });
    restaurantJson[item.restaurant] = series;
  });

  chartConfig.series = Object.keys(restaurantJson).map((restaurantId) => ({
    type: 'spline',
    name: restaurantNameJson[restaurantId],
    data: restaurantJson[restaurantId],
    marker: {
      enabled: true
    },
    point: {
      events: {
        click() {
          // eslint-disable-next-line no-undef
          window.ReactNativeWebView.postMessage(this.customValue);
        }
      }
    }
  }));
  return chartConfig;
};
