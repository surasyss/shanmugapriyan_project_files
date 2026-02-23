import React from 'react';
import { FlatList } from 'react-native';
import Invoice from '../Invoice';
import InvoiceEmpty from '../InvoiceEmpty';
import Loader from '../Loader';

export default function InvoiceList(props) {
  let {
    invoices
  } = props;
  const {
    loadNextPage, loading, firstLoad, onPress, style, emptyMessage
  } = props;
  if (!invoices) invoices = [];

  return (
    <FlatList
      style={style}
      data={invoices}
      renderItem={({ item, index }) => (
        <Invoice
          index={index}
          key={item.id.toString()}
          invoice={item}
          onPress={onPress}
        />
      )}
      onEndReached={() => loadNextPage()}
      ListFooterComponent={
                invoices.length
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
      refreshing={invoices.length !== 0 && firstLoad}
      onRefresh={() => loadNextPage(1)}
      keyExtractor={(item) => item.id.toString()}
    />
  );
}
