import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import Loader from '../Loader';
import Payment from '../Payment';

export default function PaymentList(props) {
  let {
    payments
  } = props;
  const {
    loadNextPage, loading, firstLoad, onPress, style, emptyMessage, showPaymentType, showStatus
  } = props;
  if (!payments) payments = [];

  return (
    <FlatList
      style={style}
      data={payments}
      renderItem={({ item, index }) => (
        <Payment
          showPaymentType={showPaymentType}
          showStatus={showStatus}
          index={index}
          key={item.id.toString()}
          payment={item}
          onPress={onPress}
        />
      )}
      onEndReached={() => loadNextPage()}
      ListFooterComponent={
          payments.length
            ? (
              <Loader
                loading={loading}
              />
            ) : null
            }
      ListEmptyComponent={(
        <InvoiceEmpty
          loading={loading}
          message={emptyMessage}
        />
            )}
      refreshing={payments.length !== 0 && firstLoad}
      onRefresh={() => loadNextPage(1)}
      keyExtractor={(item) => item.id.toString()}
    />
  );
}
